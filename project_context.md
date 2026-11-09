# IP-SAKTI Sahayak — Project Context

## 1. Project Overview

**Project Name:** IP-SAKTI Sahayak  
**Project Type:** Multilingual RAG-based AYUSH Prior-Art Discovery and Innovation Research Platform  
**Domain:** Artificial Intelligence, Generative AI, Information Retrieval, AYUSH, Intellectual Property Research

IP-SAKTI Sahayak is a web-based AI-assisted platform designed to help researchers, innovators, students and AYUSH practitioners investigate existing knowledge related to Ayurvedic and other AYUSH innovations.

The platform addresses the difficulty of discovering relevant prior art across scattered patent documents, traditional knowledge resources, research publications and phytochemical databases.

It uses multilingual information retrieval, Retrieval-Augmented Generation (RAG), semantic comparison and evidence-linked reporting.

## 2. Problem Statement

AYUSH-related innovations may involve medicinal plants, phytochemicals, herbal formulations, preparation methods and therapeutic applications.

Relevant information is distributed across different sources and formats, making it difficult to:

- Identify previously disclosed formulations and technical methods.
- Discover related patents and research publications.
- Identify traditional knowledge associated with ingredients.
- Compare a proposed innovation with existing disclosures.
- Understand which features are already known and which require further investigation.
- Perform research across different languages.

A simple keyword search or general-purpose chatbot cannot reliably perform these tasks.

## 3. Proposed Solution

IP-SAKTI Sahayak provides two major capabilities.

### A. Innovation Analysis

Users submit details of their proposed AYUSH innovation.

The platform:

1. Collects structured innovation information.
2. Processes supporting documents.
3. Extracts important technical features.
4. Generates multiple research queries.
5. Searches available patent, traditional knowledge, research and AYUSH datasets.
6. Retrieves relevant evidence.
7. Compares individual innovation features against retrieved disclosures.
8. Identifies similarities, differences, gaps and uncertainties.
9. Generates a structured research report with citations.

The output is a preliminary prior-art discovery and innovation research report, not a legal patentability decision.

### B. Multilingual Patent Assistant

Users can interact with an AI assistant to:

- Ask questions about AYUSH innovations.
- Search for related patents and technical disclosures.
- Investigate medicinal plants and phytochemicals.
- Understand existing research evidence.
- Ask questions about their submitted innovation.
- Explore retrieved documents.
- Ask follow-up questions.
- Communicate in supported languages.

The assistant must retrieve evidence when answering knowledge-base questions and must not invent citations or unsupported findings.

## 4. Supported Languages

Initial language support:

- English
- Hindi
- Telugu

The architecture should allow additional languages such as Tamil and Malayalam in future versions.

The system should support cross-lingual retrieval. For example, a Telugu question should be able to retrieve relevant English patent or research documents when the underlying meaning matches.

Language support must be tested independently for query understanding, retrieval and answer generation.

## 5. Target Users

- AYUSH researchers.
- Students and academic researchers.
- Herbal formulation developers.
- Innovation teams.
- Patent research professionals.
- Traditional knowledge researchers.

## 6. Main User Journey

### Step 1: Home Page

The user understands the platform's purpose and available features.

### Step 2: Create an Innovation

The user enters:

- Innovation title.
- AYUSH system.
- Innovation category.
- Problem being addressed.
- Proposed solution.
- Medicinal plants and ingredients.
- Plant parts and proportions.
- Preparation and extraction methods.
- Formulation details.
- Intended application.
- Technical advantages and differentiating features.
- Supporting documents.

### Step 3: Review and Submit

The user reviews the submitted information and creates an innovation record.

### Step 4: Run Innovation Analysis

The backend processes the innovation through the research pipeline.

The user can see genuine processing stages and their outcomes.

### Step 5: View Analysis Report

The user receives:

- Executive summary.
- Innovation profile.
- Relevant patents.
- Research publications.
- Traditional knowledge references.
- Phytochemical information.
- Feature-level comparison.
- Similarities and differences.
- Research gaps.
- Recommendations.
- Evidence-linked citations.
- Search limitations and uncertainty.

### Step 6: Ask the Patent Assistant

The user can ask questions about the report, retrieved evidence or broader AYUSH prior-art research.

### Step 7: Reanalyse and Compare

The user can update an innovation, run another analysis and compare report versions without losing previous results.

## 7. Important Product Principles

### Evidence over confident answers

Every factual research claim should be supported by retrieved evidence wherever the platform claims to provide research findings.

### No fabricated citations

A citation must correspond to an actual source and supporting passage.

### No unsupported patentability claims

The platform must not declare an invention patentable or guarantee novelty.

It should provide preliminary research observations and clearly indicate that formal legal assessment requires a qualified patent professional.

### Similarity is not patentability

A semantic similarity score must never be presented as a patentability percentage.

### Transparency

The platform should communicate:

- What sources were searched.
- What information was found.
- What was not found.
- Which evidence supports a conclusion.
- Where evidence is incomplete or conflicting.
- What limitations affect the result.

### Version history

Every analysis must be preserved as a separate version.

### Data separation

User-uploaded innovation documents are private supporting context. They must not automatically become external prior-art evidence.

## 8. Scope of the Initial Prototype

The current prototype focuses on Curcuma longa (turmeric).

The purpose is to demonstrate the complete technical workflow using a limited, identifiable corpus before expanding to other medicinal plants and AYUSH knowledge sources.

The platform must clearly disclose corpus limitations.

Do not claim comprehensive AYUSH coverage based on the turmeric prototype.

## 9. Expected Final Product

A complete web application containing:

- Responsive React frontend.
- Python backend.
- RAG-based Patent Assistant.
- Innovation submission and management.
- Automated prior-art research pipeline.
- Evidence-linked comparison.
- Structured report generation.
- Multilingual interaction.
- Analysis transparency.
- Version history.
- Secure document handling.
- Evaluation and testing framework.

## 10. Project Success Criteria

The prototype should demonstrate that:

1. A user can submit an innovation.
2. The system can extract and structure its technical features.
3. The system can retrieve relevant external evidence.
4. Retrieved evidence can be compared against individual features.
5. The report contains verifiable citations.
6. The assistant can answer grounded questions.
7. The assistant can handle follow-up questions and unrelated questions appropriately.
8. The system can abstain when evidence is insufficient.
9. Previous analysis versions remain accessible.
10. The user can understand what the system actually searched and verified.