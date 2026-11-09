"""Compile IMPPAT raw TSV files into rich, structured traditional knowledge documents for RAG.

This generates:
1. data/documents/traditional_knowledge/ayurvedic_formulary_of_india_polyherbal.md
2. data/documents/traditional_knowledge/ayurvedic_pharmacopoeia_of_india_singleherbal.md
3. data/documents/traditional_knowledge/imppat_medicinal_plants_reference.md
"""
from __future__ import annotations
import csv
import sys
from collections import defaultdict
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

DATA_DIR = Path("data/documents")
TK_DIR = DATA_DIR / "traditional_knowledge"
TK_DIR.mkdir(parents=True, exist_ok=True)


def compile_polyherbal():
    tsv_path = DATA_DIR / "IMPPAT_PolyHerbalFormulations.tsv"
    if not tsv_path.exists():
        print(f"Skipping polyherbal: {tsv_path} not found.")
        return

    forms = defaultdict(lambda: {"ingredients": [], "plants": set(), "uses": "", "ref": ""})
    with open(tsv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            fid = row.get("Formulation_identifier", "").strip()
            fname = row.get("Formulation name_in_AFI_original", "").strip()
            if not fname:
                continue
            key = (fid, fname)
            ing = row.get("Ingredient_name_standardised", "").strip() or row.get("Ingredient name in AFI_original", "").strip()
            part = row.get("Plant_part_standardised", "").strip() or row.get("Plant part in AFI_original", "").strip()
            plant = row.get("Plant_name_standardised", "").strip()
            uses = row.get("Therapeutic uses (according to The Ayurvedic Formulary of India)", "").strip() or row.get("Therapeutic_uses_standardised", "").strip()
            ref = row.get("References", "").strip()
            if ing:
                forms[key]["ingredients"].append(f"{ing} ({part})" if part else ing)
            if plant:
                forms[key]["plants"].add(plant)
            if uses and not forms[key]["uses"]:
                forms[key]["uses"] = uses
            if ref and not forms[key]["ref"]:
                forms[key]["ref"] = ref

    out_file = TK_DIR / "ayurvedic_formulary_of_india_polyherbal.md"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("# The Ayurvedic Formulary of India (AFI) — Polyherbal Formulations\n\n")
        f.write("Traditional Ayurvedic polyherbal formulation references, constituent medicinal plants, plant parts, and documented therapeutic uses.\n\n")
        for (fid, fname), data in forms.items():
            f.write(f"## Formulation: {fname}\n")
            f.write(f"- Formulation Identifier: {fid}\n")
            f.write("- Traditional System: Ayurveda\n")
            f.write(f"- Source Document: The Ayurvedic Formulary of India (AFI)\n")
            if data["ref"]:
                f.write(f"- Reference: {data['ref']}\n")
            if data["uses"]:
                f.write(f"- Documented Traditional Therapeutic Uses: {data['uses']}\n")
            if data["plants"]:
                f.write(f"- Constituent Botanical Plants: {', '.join(sorted(data['plants']))}\n")
            if data["ingredients"]:
                f.write(f"- Ingredients and Plant Parts: {', '.join(data['ingredients'])}\n")
            f.write("\n")
    print(f"Compiled {len(forms)} AFI polyherbal formulations into {out_file.name}")


def compile_singleherbal():
    tsv_path = DATA_DIR / "IMPPAT_SingleHerbalFormulations.tsv"
    if not tsv_path.exists():
        print(f"Skipping single herbal: {tsv_path} not found.")
        return

    forms = []
    with open(tsv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            fid = row.get("Formulation_identifier", "").strip()
            fname = row.get("Formulation_name_in_API_original", "").strip()
            plant = row.get("Plant_name_standardised", "").strip() or row.get("Ingredient name in API_original", "").strip()
            part = row.get("Plant_part_standardised", "").strip() or row.get("Plant part in API_original", "").strip()
            uses = row.get("Therapeutic_uses_standardised", "").strip() or row.get("Therapeutic_uses (according to The Ayurvedic Pharmacopoeia of India)", "").strip()
            ref = row.get("References", "").strip()
            if fname or plant:
                forms.append({
                    "fid": fid,
                    "name": fname or plant,
                    "plant": plant,
                    "part": part,
                    "uses": uses,
                    "ref": ref
                })

    out_file = TK_DIR / "ayurvedic_pharmacopoeia_of_india_singleherbal.md"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("# The Ayurvedic Pharmacopoeia of India (API) — Single Herbal Formulations\n\n")
        f.write("Official single herbal monograph references, standard plant parts, and documented therapeutic uses from the Ayurvedic Pharmacopoeia of India.\n\n")
        for item in forms:
            f.write(f"## Single Herbal Formulation: {item['name']}\n")
            if item["fid"]:
                f.write(f"- Formulation Identifier: {item['fid']}\n")
            f.write("- Traditional System: Ayurveda\n")
            f.write("- Source Document: The Ayurvedic Pharmacopoeia of India (API)\n")
            if item["plant"]:
                f.write(f"- Botanical Plant: {item['plant']}\n")
            if item["part"]:
                f.write(f"- Plant Part Used: {item['part']}\n")
            if item["uses"]:
                f.write(f"- Documented Traditional Therapeutic Uses: {item['uses']}\n")
            if item["ref"]:
                f.write(f"- Reference: {item['ref']}\n")
            f.write("\n")
    print(f"Compiled {len(forms)} API single herbal formulations into {out_file.name}")


def compile_plants():
    plants_tsv = DATA_DIR / "Plant_Information_IMPPAT.tsv"
    uses_tsv = DATA_DIR / "IMPPAT_TherapeuticUse_Plant_Association.tsv"
    if not plants_tsv.exists():
        print(f"Skipping plants: {plants_tsv} not found.")
        return

    # Load therapeutic uses grouped by plant
    plant_uses = defaultdict(set)
    if uses_tsv.exists():
        with open(uses_tsv, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                p = row.get("Indian_Medicinal_plant", "").strip()
                u = row.get("Therapeutic_use", "").strip()
                if p and u:
                    plant_uses[p].add(u)

    plants_data = []
    with open(plants_tsv, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            pname = row.get("Indian_Medicinal_plant", "").strip()
            if not pname:
                continue
            common = row.get("Common_name", "").strip()
            synonyms = row.get("Synonymous names", "").strip()
            family = row.get("Family", "").strip()
            systems = row.get("System_of_Medicine", "").strip()
            uses = sorted(plant_uses.get(pname, []))

            # Focus on plants with known systems or therapeutic uses
            if systems or uses or common:
                plants_data.append({
                    "name": pname,
                    "common": common,
                    "synonyms": synonyms,
                    "family": family,
                    "systems": systems or "Traditional Indian Medicine",
                    "uses": uses[:25],  # top uses for conciseness
                })

    out_file = TK_DIR / "imppat_medicinal_plants_reference.md"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("# IMPPAT Indian Medicinal Plants Reference\n\n")
        f.write("Standardized database of Indian medicinal plants, botanical synonyms, traditional medicine systems (Ayurveda, Siddha, Unani), and documented therapeutic uses.\n\n")
        for item in plants_data:
            f.write(f"## Medicinal Plant: {item['name']}\n")
            if item["common"]:
                f.write(f"- Common Name: {item['common']}\n")
            if item["synonyms"]:
                f.write(f"- Botanical Synonyms: {item['synonyms']}\n")
            if item["family"]:
                f.write(f"- Botanical Family: {item['family']}\n")
            f.write(f"- Traditional Medical Systems: {item['systems']}\n")
            if item["uses"]:
                f.write(f"- Documented Traditional Therapeutic Uses: {', '.join(item['uses'])}\n")
            f.write("\n")
    print(f"Compiled {len(plants_data)} medicinal plants into {out_file.name}")


if __name__ == "__main__":
    compile_polyherbal()
    compile_singleherbal()
    compile_plants()
    print("IMPPAT compilation complete.")

