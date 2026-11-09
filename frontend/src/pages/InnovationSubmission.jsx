import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  Lightbulb, 
  Plus, 
  Trash2, 
  Sparkles, 
  RotateCcw, 
  ArrowRight, 
  AlertCircle, 
  CheckCircle2, 
  AlertTriangle,
  FlaskConical,
  Layers,
  FileText,
  UploadCloud,
  File,
  Eye,
  EyeOff,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  History,
  FolderKanban,
  BookOpen,
  Scale
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useInnovation } from '../context/InnovationContext';
import { 
  uploadInnovationDocument, 
  deleteInnovationDocument,
  getInnovation,
  createInnovation,
  updateInnovation
} from '../api/client';

const DEFAULT_AYUSH_SYSTEMS = [
  'Ayurveda',
  'Siddha',
  'Unani',
  'Homeopathy',
  'Sowa-Rigpa',
  'General AYUSH'
];

const INITIAL_INGREDIENT = {
  scientificName: '',
  commonName: '',
  plantPart: '',
  quantity: ''
};

const DEMO_EXAMPLE = {
  title: 'Synergistic Topical Emulgel of Curcuma longa and Piper nigrum for Accelerated Wound Healing',
  ayushSystem: 'Ayurveda',
  problem: 'Poor dermal bioavailability, chemical instability, and rapid degradation of topical curcumin in open wound healing.',
  solution: 'A stable topical emulgel incorporating standardized Curcuma longa rhizome extract with piperine in a carbopol polymer matrix.',
  ingredients: [
    {
      scientificName: 'Curcuma longa',
      commonName: 'Turmeric / Haridra',
      plantPart: 'Rhizome extract',
      quantity: 'Standardized 95% total curcuminoids'
    },
    {
      scientificName: 'Piper nigrum',
      commonName: 'Black Pepper / Maricha',
      plantPart: 'Fruit extract / Piperine',
      quantity: '1:10 w/w ratio to curcumin'
    },
    {
      scientificName: 'Carbopol 940',
      commonName: 'Carbomer',
      plantPart: 'Synthetic polymer base',
      quantity: '1.0% w/v'
    },
    {
      scientificName: 'Triethanolamine',
      commonName: 'TEA',
      plantPart: 'Neutralizer',
      quantity: 'q.s. to pH 6.0 - 6.5'
    }
  ],
  technicalFeatures: [
    'Standardized Curcuma longa extract containing 95% total curcuminoids',
    'Piperine bio-enhancer at 1:10 w/w ratio to curcumin for increased dermal permeation',
    'Topical carbopol emulgel formulation maintaining stable pH 6.0 - 6.5',
    'Demonstrated 2.5-fold acceleration in epithelial wound closure over single herbs'
  ],
  claimedAdvantages: 'Enhanced dermal penetration, prolonged active retention, and synergistic wound healing without systemic toxicity.'
};

function formatBytes(bytes, decimals = 1) {
  if (!bytes) return '0 B';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

export default function InnovationSubmission() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated } = useAuth();
  const { 
    runAnalysis, 
    isAnalyzing, 
    analysisError, 
    uploadedDocuments, 
    setUploadedDocuments 
  } = useInnovation();

  const searchParams = new URLSearchParams(location.search);
  const editingId = searchParams.get('id');

  // Form State
  const [title, setTitle] = useState('');
  const [ayushSystem, setAyushSystem] = useState('Ayurveda');
  const [problem, setProblem] = useState('');
  const [solution, setSolution] = useState('');
  const [ingredients, setIngredients] = useState([{ ...INITIAL_INGREDIENT }]);
  const [technicalFeatures, setTechnicalFeatures] = useState(['']);
  const [claimedAdvantages, setClaimedAdvantages] = useState('');

  // Versioning state
  const [loadedProject, setLoadedProject] = useState(null);
  const [selectedVersionNum, setSelectedVersionNum] = useState(null);

  // Document Upload State
  const [isDragging, setIsDragging] = useState(false);
  const [expandedPreviews, setExpandedPreviews] = useState({});
  const fileInputRef = useRef(null);

  // Field-specific validation errors
  const [errors, setErrors] = useState({});

  // Load existing project from MySQL if ID provided
  useEffect(() => {
    if (!editingId || !isAuthenticated) return;
    let isMounted = true;
    getInnovation(editingId)
      .then((data) => {
        if (!isMounted || !data.innovation) return;
        const inn = data.innovation;
        setLoadedProject(inn);
        const latest = inn.latest_version;
        if (latest) {
          setTitle(latest.title || inn.title);
          setAyushSystem(latest.ayush_system || inn.ayush_system);
          setProblem(latest.problem || '');
          setSolution(latest.solution || '');
          setClaimedAdvantages(latest.claimed_advantages || '');
          setSelectedVersionNum(latest.version_number);

          if (Array.isArray(latest.ingredients) && latest.ingredients.length > 0) {
            setIngredients(
              latest.ingredients.map((ing) => ({
                scientificName: typeof ing === 'string' ? ing : ing.scientificName || '',
                commonName: ing.commonName || '',
                plantPart: ing.plantPart || '',
                quantity: ing.quantity || '',
              }))
            );
          }
          if (Array.isArray(latest.technical_features) && latest.technical_features.length > 0) {
            setTechnicalFeatures([...latest.technical_features]);
          }
        }
      })
      .catch((err) => {
        console.warn('Could not load innovation from MySQL:', err);
      });
    return () => {
      isMounted = false;
    };
  }, [editingId, isAuthenticated]);

  // Handle switching between historical versions
  const handleSelectHistoricalVersion = (vNum) => {
    if (!loadedProject || !loadedProject.versions) return;
    const targetVersion = loadedProject.versions.find((v) => v.version_number === parseInt(vNum, 10));
    if (!targetVersion) return;

    setSelectedVersionNum(targetVersion.version_number);
    setTitle(targetVersion.title || loadedProject.title);
    setAyushSystem(targetVersion.ayush_system || loadedProject.ayush_system);
    setProblem(targetVersion.problem || '');
    setSolution(targetVersion.solution || '');
    setClaimedAdvantages(targetVersion.claimed_advantages || '');

    if (Array.isArray(targetVersion.ingredients) && targetVersion.ingredients.length > 0) {
      setIngredients(
        targetVersion.ingredients.map((ing) => ({
          scientificName: typeof ing === 'string' ? ing : ing.scientificName || '',
          commonName: ing.commonName || '',
          plantPart: ing.plantPart || '',
          quantity: ing.quantity || '',
        }))
      );
    }
    if (Array.isArray(targetVersion.technical_features) && targetVersion.technical_features.length > 0) {
      setTechnicalFeatures([...targetVersion.technical_features]);
    }
  };

  // ----------------------------------------------------------------------------
  // Document Upload Handlers
  // ----------------------------------------------------------------------------
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileInputChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(Array.from(e.target.files));
    }
    // reset input so the same file can be re-selected if removed
    e.target.value = '';
  };

  const handleFiles = async (files) => {
    for (const file of files) {
      const tempId = 'temp_' + Date.now() + '_' + Math.random().toString(36).substring(2, 8);
      const initialEntry = {
        id: tempId,
        filename: file.name,
        file_size: file.size,
        file_type: file.name.split('.').pop().toLowerCase(),
        status: 'uploading',
        progress: 10,
        extracted_text: '',
        page_count: 0,
        warnings: [],
        error: null,
      };

      setUploadedDocuments((prev) => [...prev, initialEntry]);

      try {
        const result = await uploadInnovationDocument(file, (percent) => {
          setUploadedDocuments((prev) =>
            prev.map((item) => (item.id === tempId ? { ...item, progress: percent } : item))
          );
        });

        setUploadedDocuments((prev) =>
          prev.map((item) =>
            item.id === tempId
              ? {
                  ...result,
                  id: result.document_id || tempId,
                  progress: 100,
                  status: result.status || 'success',
                }
              : item
          )
        );
      } catch (err) {
        setUploadedDocuments((prev) =>
          prev.map((item) =>
            item.id === tempId
              ? {
                  ...item,
                  status: 'error',
                  progress: 100,
                  error: err.message || 'File upload failed.',
                }
              : item
          )
        );
      }
    }
  };

  const handleRemoveDocument = async (docId, storedDocId) => {
    if (storedDocId && storedDocId.startsWith('doc_')) {
      try {
        await deleteInnovationDocument(storedDocId);
      } catch (err) {
        console.warn('Failed to delete document from sandbox:', err);
      }
    }
    setUploadedDocuments((prev) => prev.filter((d) => d.id !== docId && d.document_id !== docId));
  };

  const togglePreview = (id) => {
    setExpandedPreviews((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  // ----------------------------------------------------------------------------
  // Ingredient Management
  // ----------------------------------------------------------------------------
  const handleIngredientChange = (index, field, value) => {
    const updated = [...ingredients];
    updated[index][field] = value;
    setIngredients(updated);
    if (errors.ingredients) {
      setErrors((prev) => ({ ...prev, ingredients: null }));
    }
  };

  const addIngredient = () => {
    setIngredients([...ingredients, { ...INITIAL_INGREDIENT }]);
  };

  const removeIngredient = (index) => {
    if (ingredients.length > 1) {
      setIngredients(ingredients.filter((_, i) => i !== index));
    }
  };

  // ----------------------------------------------------------------------------
  // Technical Features Management
  // ----------------------------------------------------------------------------
  const handleFeatureChange = (index, value) => {
    const updated = [...technicalFeatures];
    updated[index] = value;
    setTechnicalFeatures(updated);
    if (errors.technicalFeatures) {
      setErrors((prev) => ({ ...prev, technicalFeatures: null }));
    }
  };

  const addFeature = () => {
    setTechnicalFeatures([...technicalFeatures, '']);
  };

  const removeFeature = (index) => {
    if (technicalFeatures.length > 1) {
      setTechnicalFeatures(technicalFeatures.filter((_, i) => i !== index));
    }
  };

  // ----------------------------------------------------------------------------
  // Demo Loader & Form Reset
  // ----------------------------------------------------------------------------
  const loadDemo = () => {
    setTitle(DEMO_EXAMPLE.title);
    setAyushSystem(DEMO_EXAMPLE.ayushSystem);
    setProblem(DEMO_EXAMPLE.problem);
    setSolution(DEMO_EXAMPLE.solution);
    setIngredients(DEMO_EXAMPLE.ingredients.map((ing) => ({ ...ing })));
    setTechnicalFeatures([...DEMO_EXAMPLE.technicalFeatures]);
    setClaimedAdvantages(DEMO_EXAMPLE.claimedAdvantages);
    setErrors({});
  };

  const clearForm = () => {
    setTitle('');
    setAyushSystem('Ayurveda');
    setProblem('');
    setSolution('');
    setIngredients([{ ...INITIAL_INGREDIENT }]);
    setTechnicalFeatures(['']);
    setClaimedAdvantages('');
    setUploadedDocuments([]);
    setErrors({});
  };

  // ----------------------------------------------------------------------------
  // Validation & Submission
  // ----------------------------------------------------------------------------
  const validateForm = () => {
    const newErrors = {};

    if (!title.trim()) {
      newErrors.title = 'Innovation title is required.';
    }

    // Must have at least one ingredient with a non-empty scientific/botanical name
    const validIngredients = ingredients.filter(
      (ing) => ing.scientificName && ing.scientificName.trim()
    );
    if (validIngredients.length === 0) {
      newErrors.ingredients = 'At least one ingredient or botanical substance is required.';
    }

    // Must have at least one technical feature
    const validFeatures = technicalFeatures.filter((f) => f && f.trim());
    if (validFeatures.length === 0) {
      newErrors.technicalFeatures = 'At least one distinguishing technical feature is required for prior-art comparison.';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isAnalyzing) return;

    if (!validateForm()) {
      return;
    }

    // Format structured ingredients for backend consumption
    const formattedIngredients = ingredients
      .filter((ing) => ing.scientificName && ing.scientificName.trim())
      .map((ing) => {
        const parts = [ing.scientificName.trim()];
        if (ing.commonName?.trim()) parts.push(`(${ing.commonName.trim()})`);
        if (ing.plantPart?.trim()) parts.push(ing.plantPart.trim());
        if (ing.quantity?.trim()) parts.push(ing.quantity.trim());
        return parts.join(' ');
      });

    const formattedFeatures = technicalFeatures
      .map((f) => f.trim())
      .filter((f) => f.length > 0);

    // Filter successfully extracted applicant documents
    const validDocs = uploadedDocuments
      .filter((d) => d.status === 'success' || d.status === 'warning')
      .map((d) => ({
        document_id: d.document_id || d.id,
        filename: d.filename,
        page_count: d.page_count || 1,
        file_type: d.file_type || '',
        extracted_text: d.extracted_text || '',
        warnings: d.warnings || [],
      }));

    const payload = {
      title: title.trim(),
      ayush_system: ayushSystem,
      problem: problem.trim() || 'Not specified by applicant',
      solution: solution.trim() || 'Not specified by applicant',
      ingredients: formattedIngredients,
      technical_features: formattedFeatures,
      claimed_advantages: claimedAdvantages.trim() || 'None specified by applicant',
      uploaded_documents: validDocs,
    };

    try {
      await runAnalysis(payload);
      navigate('/report');
    } catch (err) {
      // Handled via context analysisError
    }
  };

  return (
    <div>
      {/* Header Banner */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Lightbulb size={24} color="var(--accent-primary)" />
              <span>Innovation Prior-Art Submission</span>
            </h1>
            <p style={{ fontSize: '0.92rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Submit an AYUSH formulation or technical composition for automated multi-query retrieval and statutory feature-level comparison.
            </p>
          </div>
          
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              type="button"
              onClick={loadDemo}
              disabled={isAnalyzing}
              className="btn btn-secondary"
              style={{ fontSize: '0.85rem' }}
            >
              <Sparkles size={16} color="var(--accent-secondary)" />
              <span>Load Demonstration Example</span>
            </button>
            <button
              type="button"
              onClick={clearForm}
              disabled={isAnalyzing}
              className="btn btn-secondary"
              style={{ fontSize: '0.85rem' }}
            >
              <RotateCcw size={16} />
              <span>Reset Form</span>
            </button>
          </div>
        </div>
      </div>

      {analysisError && (
        <div className="alert alert-danger" style={{ marginBottom: '20px' }}>
          <AlertCircle size={20} style={{ flexShrink: 0 }} />
          <div>
            <div style={{ fontWeight: 600 }}>Analysis Request Error</div>
            <div style={{ fontSize: '0.88rem' }}>{analysisError}</div>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        {/* Section 1: Overview */}
        <div className="form-section">
          <div className="form-section-title">
            <FlaskConical size={18} color="var(--accent-secondary)" />
            <span>1. Innovation Overview & Applicant Claims</span>
          </div>

          <div className="form-group">
            <label className="form-label">
              Innovation Title <span className="required" style={{ color: 'var(--danger)' }}>*</span>
            </label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. Synergistic Topical Emulgel of Curcuma longa and Piper nigrum for Accelerated Wound Healing"
              value={title}
              onChange={(e) => {
                setTitle(e.target.value);
                if (errors.title) setErrors((prev) => ({ ...prev, title: null }));
              }}
            />
            {errors.title && (
              <div className="field-error">
                <AlertCircle size={14} />
                <span>{errors.title}</span>
              </div>
            )}
          </div>

          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">AYUSH Traditional Knowledge System</label>
              <select
                className="form-control"
                value={ayushSystem}
                onChange={(e) => setAyushSystem(e.target.value)}
              >
                {DEFAULT_AYUSH_SYSTEMS.map((sys) => (
                  <option key={sys} value={sys}>
                    {sys}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Claimed Advantages / Novel Effect (Applicant Claim)</label>
              <input
                type="text"
                className="form-control"
                placeholder="e.g. Enhanced dermal bioavailability, 2.5x acceleration in wound closure"
                value={claimedAdvantages}
                onChange={(e) => setClaimedAdvantages(e.target.value)}
              />
            </div>
          </div>

          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">Technical Problem Addressed (Applicant Claim)</label>
              <textarea
                className="form-control"
                rows={3}
                placeholder="Describe limitations, instability, or poor efficacy in existing formulations..."
                value={problem}
                onChange={(e) => setProblem(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Proposed Technical Solution (Applicant Claim)</label>
              <textarea
                className="form-control"
                rows={3}
                placeholder="Describe the technical formulation, delivery matrix, or processing method..."
                value={solution}
                onChange={(e) => setSolution(e.target.value)}
              />
            </div>
          </div>
        </div>

        {/* Section 2: Botanical Ingredients */}
        <div className="form-section">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '10px' }}>
            <div className="form-section-title" style={{ margin: 0, padding: 0, border: 'none' }}>
              <Layers size={18} color="var(--success)" />
              <span>2. Ingredients & Formulation Components <span className="required" style={{ color: 'var(--danger)' }}>*</span></span>
            </div>
            <button
              type="button"
              onClick={addIngredient}
              className="btn btn-secondary"
              style={{ fontSize: '0.8rem', padding: '6px 12px' }}
            >
              <Plus size={14} />
              <span>Add Ingredient</span>
            </button>
          </div>

          <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginBottom: '14px' }}>
            Specify the botanical or chemical ingredients. Botanical names are matched against IMPPAT and traditional AYUSH pharmacopoeias.
          </p>

          {errors.ingredients && (
            <div className="field-error" style={{ marginBottom: '14px' }}>
              <AlertCircle size={14} />
              <span>{errors.ingredients}</span>
            </div>
          )}

          {ingredients.map((ing, idx) => (
            <div key={idx} className="card" style={{ padding: '14px', marginBottom: '12px', backgroundColor: 'var(--bg-secondary)' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.5fr 1.5fr 1.5fr auto', gap: '10px', alignItems: 'center' }}>
                <div>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Botanical / Scientific Name (e.g. Curcuma longa)"
                    value={ing.scientificName}
                    onChange={(e) => handleIngredientChange(idx, 'scientificName', e.target.value)}
                  />
                </div>
                <div>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Common / AYUSH Name (e.g. Haridra)"
                    value={ing.commonName}
                    onChange={(e) => handleIngredientChange(idx, 'commonName', e.target.value)}
                  />
                </div>
                <div>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Plant Part (e.g. Rhizome extract)"
                    value={ing.plantPart}
                    onChange={(e) => handleIngredientChange(idx, 'plantPart', e.target.value)}
                  />
                </div>
                <div>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Quantity / Spec (e.g. 95% curcuminoids)"
                    value={ing.quantity}
                    onChange={(e) => handleIngredientChange(idx, 'quantity', e.target.value)}
                  />
                </div>
                <div>
                  <button
                    type="button"
                    onClick={() => removeIngredient(idx)}
                    disabled={ingredients.length <= 1}
                    className="btn-icon-danger"
                    title="Remove ingredient"
                    style={{ opacity: ingredients.length <= 1 ? 0.3 : 1, cursor: ingredients.length <= 1 ? 'not-allowed' : 'pointer' }}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Section 3: Technical Features */}
        <div className="form-section">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '10px' }}>
            <div className="form-section-title" style={{ margin: 0, padding: 0, border: 'none' }}>
              <FileText size={18} color="#38bdf8" />
              <span>3. Distinguishing Technical Features & Parameters <span className="required" style={{ color: 'var(--danger)' }}>*</span></span>
            </div>
            <button
              type="button"
              onClick={addFeature}
              className="btn btn-secondary"
              style={{ fontSize: '0.8rem', padding: '6px 12px' }}
            >
              <Plus size={14} />
              <span>Add Technical Feature</span>
            </button>
          </div>

          <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginBottom: '14px' }}>
            Provide individual technical parameters (e.g. standardization thresholds, synergistic ratio, delivery matrix, pH, comparative efficacy). Each feature is evaluated separately against prior-art evidence.
          </p>

          {errors.technicalFeatures && (
            <div className="field-error" style={{ marginBottom: '14px' }}>
              <AlertCircle size={14} />
              <span>{errors.technicalFeatures}</span>
            </div>
          )}

          {technicalFeatures.map((feat, idx) => (
            <div key={idx} style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '10px' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', width: '24px' }}>
                {idx + 1}.
              </span>
              <input
                type="text"
                className="form-control"
                placeholder="e.g. Standardized Curcuma longa extract containing 95% total curcuminoids..."
                value={feat}
                onChange={(e) => handleFeatureChange(idx, e.target.value)}
              />
              <button
                type="button"
                onClick={() => removeFeature(idx)}
                disabled={technicalFeatures.length <= 1}
                className="btn-icon-danger"
                title="Remove feature"
                style={{ opacity: technicalFeatures.length <= 1 ? 0.3 : 1, cursor: technicalFeatures.length <= 1 ? 'not-allowed' : 'pointer' }}
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>

        {/* Section 4: Document Upload & Extraction (Phase 5) */}
        <div className="form-section">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '10px' }}>
            <div className="form-section-title" style={{ margin: 0, padding: 0, border: 'none' }}>
              <UploadCloud size={18} color="var(--accent-secondary)" />
              <span>4. Applicant Innovation Documentation (Optional)</span>
            </div>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="btn btn-secondary"
              style={{ fontSize: '0.8rem', padding: '6px 12px' }}
            >
              <File size={14} />
              <span>Browse Files</span>
            </button>
          </div>

          <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginBottom: '14px' }}>
            Attach laboratory reports, patent specifications, or formulation monographs (PDF, DOCX, TXT up to 15 MB).
            Text is extracted automatically via sandboxed PyMuPDF and python-docx.
          </p>

          {/* Hidden File Input */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.txt"
            style={{ display: 'none' }}
            onChange={handleFileInputChange}
          />

          {/* Drag & Drop Zone */}
          <div
            className={`upload-dropzone ${isDragging ? 'drag-active' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <div className="upload-icon-circle">
              <UploadCloud size={26} />
            </div>
            <div style={{ fontSize: '0.96rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
              Drag and drop your patent draft or specification here
            </div>
            <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              or click to browse from your device
            </div>

            <div className="upload-supported-badges">
              <span className="upload-type-pill">PDF </span>
              <span className="upload-type-pill">DOCX</span>
              <span className="upload-type-pill">TXT</span>
              <span className="upload-type-pill">Max 15 MB</span>
            </div>
          </div>

          {/* Uploaded Documents List */}
          {uploadedDocuments && uploadedDocuments.length > 0 && (
            <div style={{ marginTop: '18px' }}>
              <div style={{ fontSize: '0.84rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '10px' }}>
                Uploaded Documents ({uploadedDocuments.length})
              </div>

              {uploadedDocuments.map((doc) => {
                const docId = doc.id || doc.document_id;
                const isUploading = doc.status === 'uploading';
                const isSuccess = doc.status === 'success';
                const isWarning = doc.status === 'warning';
                const isError = doc.status === 'error';
                const isExpanded = !!expandedPreviews[docId];

                return (
                  <div
                    key={docId}
                    className={`upload-file-card ${isError ? 'has-error' : ''} ${isWarning ? 'has-warning' : ''}`}
                  >
                    <div className="upload-file-header">
                      <div className="upload-file-info">
                        <div className="upload-file-icon">
                          <File size={20} />
                        </div>
                        <div className="upload-file-meta">
                          <div className="upload-file-name" title={doc.filename}>
                            {doc.filename}
                          </div>
                          <div className="upload-file-subtext">
                            <span>{formatBytes(doc.file_size)}</span>
                            {doc.page_count > 0 && (
                              <>
                                <span>•</span>
                                <span className="extracted-page-badge">
                                  {doc.page_count} {doc.page_count === 1 ? 'page' : 'pages'}
                                </span>
                              </>
                            )}
                            {doc.text_length > 0 && (
                              <>
                                <span>•</span>
                                <span>{doc.text_length.toLocaleString()} characters</span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="upload-file-actions">
                        {/* Status Pills */}
                        {isUploading && (
                          <span style={{ fontSize: '0.75rem', color: 'var(--accent-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <div className="spinner" style={{ width: '14px', height: '14px' }} />
                            <span>Extracting...</span>
                          </span>
                        )}
                        {isSuccess && (
                          <span className="badge badge-success" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                            <CheckCircle2 size={12} />
                            <span>Extracted</span>
                          </span>
                        )}
                        {isWarning && (
                          <span className="badge badge-warning" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                            <AlertTriangle size={12} />
                            <span>Extraction Notice</span>
                          </span>
                        )}
                        {isError && (
                          <span className="badge badge-danger" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                            <AlertCircle size={12} />
                            <span>Failed</span>
                          </span>
                        )}

                        {/* Preview Extracted Text Toggle */}
                        {doc.extracted_text && (
                          <button
                            type="button"
                            className="btn btn-secondary"
                            style={{ fontSize: '0.76rem', padding: '4px 10px' }}
                            onClick={() => togglePreview(docId)}
                          >
                            {isExpanded ? <EyeOff size={13} /> : <Eye size={13} />}
                            <span>{isExpanded ? 'Hide' : 'Review Text'}</span>
                          </button>
                        )}

                        {/* Remove File Button */}
                        <button
                          type="button"
                          className="btn-icon-danger"
                          title="Remove file from submission"
                          onClick={() => handleRemoveDocument(docId, doc.document_id)}
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </div>

                    {/* Progress Bar while uploading */}
                    {isUploading && (
                      <div className="upload-progress-track">
                        <div className="upload-progress-fill" style={{ width: `${doc.progress || 35}%` }} />
                      </div>
                    )}

                    {/* Extraction Warnings */}
                    {doc.warnings && doc.warnings.length > 0 && (
                      <div className="alert alert-warning" style={{ marginTop: '10px', marginBottom: '0', padding: '8px 12px' }}>
                        <AlertTriangle size={15} style={{ flexShrink: 0 }} />
                        <div style={{ fontSize: '0.8rem' }}>
                          {doc.warnings.join(' • ')}
                        </div>
                      </div>
                    )}

                    {/* Error message */}
                    {isError && doc.error && (
                      <div className="alert alert-danger" style={{ marginTop: '10px', marginBottom: '0', padding: '8px 12px' }}>
                        <AlertCircle size={15} style={{ flexShrink: 0 }} />
                        <div style={{ fontSize: '0.8rem' }}>{doc.error}</div>
                      </div>
                    )}

                    {/* Extracted Text Preview Drawer */}
                    {isExpanded && doc.extracted_text && (
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '10px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                          <span>Extracted Content Preview (Sandbox Extracted):</span>
                          <span>{doc.extracted_text.length} characters</span>
                        </div>
                        <div className="extracted-preview-box">
                          {doc.extracted_text}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Confidentiality Callout */}
          <div className="alert alert-info" style={{ marginTop: '16px', marginBottom: 0, padding: '10px 14px' }}>
            <ShieldCheck size={18} color="var(--accent-secondary)" style={{ flexShrink: 0 }} />
            <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              <strong style={{ color: 'var(--text-primary)' }}>Confidential Applicant Sandbox:</strong> Uploaded documents are treated as private applicant disclosures.
              They are <strong>NEVER</strong> written to the public/shared and are not treated as externally verified facts.
            </div>
          </div>
        </div>

        {/* Submit Actions */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
          <button
            type="submit"
            disabled={isAnalyzing}
            className="btn btn-primary"
            style={{ padding: '12px 28px', fontSize: '1rem', fontWeight: 600 }}
          >
            <span>{isAnalyzing ? 'Analyzing Prior Art...' : ' Run Prior-Art Analysis'}</span>
            <ArrowRight size={18} />
          </button>
        </div>
      </form>

      {/* In-Depth Prior-Art Analysis Progress Modal */}
      {isAnalyzing && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.82)',
            backdropFilter: 'blur(8px)',
            zIndex: 9999,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px',
          }}
        >
          <div
            className="card"
            style={{
              maxWidth: '560px',
              width: '100%',
              textAlign: 'center',
              padding: '36px 30px',
              border: '1px solid var(--accent-primary)',
              boxShadow: '0 24px 48px rgba(0, 0, 0, 0.6)',
              background: 'var(--bg-secondary)',
            }}
          >
            <div
              className="spinner"
              style={{
                width: '46px',
                height: '46px',
                margin: '0 auto 20px',
                borderWidth: '3px',
                borderTopColor: 'var(--accent-primary)',
              }}
            />

            <h3 style={{ fontSize: '1.28rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '8px' }}>
              Performing In-Depth Prior-Art Audit...
            </h3>
            <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginBottom: '24px', lineHeight: 1.5 }}>
              Deconstructing claims, executing cross-corpus retrieval against classical treatises and patent filings, and auditing statutory requirements.
            </p>

            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
                textAlign: 'left',
                background: 'var(--bg-primary)',
                padding: '18px',
                borderRadius: '8px',
                border: '1px solid var(--border-subtle)',
                fontSize: '0.84rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#38bdf8' }}>
                <Sparkles size={16} style={{ flexShrink: 0 }} />
                <span>1. Decomposing features into multi-angle botanical & patent queries</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-secondary)' }}>
                <BookOpen size={16} style={{ flexShrink: 0 }} />
                <span>2. Searching classical AFI/API treatises & IMPPAT phytochemical records</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-secondary)' }}>
                <Layers size={16} style={{ flexShrink: 0 }} />
                <span>3. Fusing dense neural embeddings & BM25 lexical candidates (RRF)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-secondary)' }}>
                <Scale size={16} style={{ flexShrink: 0 }} />
                <span>4. Synthesizing Section 3(p) & 3(e) statutory novelty & synergy analysis</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-secondary)' }}>
                <ShieldCheck size={16} style={{ flexShrink: 0 }} />
                <span>5. Auditing 4-field passage citations against retrieved evidence</span>
              </div>
            </div>

            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '18px' }}>
              Deep multi-corpus statutory audits typically take ~15–25 seconds. Please do not close this window.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
