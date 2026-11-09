
import csv
import json
from pathlib import Path
from collections import defaultdict

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "documents"

OUTPUT_DIR = BASE_DIR / "data" / "processed" / "imppat_curcuma"
OUTPUT_FILE = OUTPUT_DIR / "curcuma_records.jsonl"

PLANT_ID = "IMPPAT3_PLTID000933"
PLANT_NAME = "Curcuma longa"

FILES = {
    "plants": "Plant_Information_IMPPAT.tsv",
    "chemicals": "Chemical_Information_IMPPAT_Phytochemicals.tsv",
    "plant_chemicals": "IMPPAT_Phytochemical_Plant_Association.tsv",
    "bioactivity": "Bioactivity_IMPPAT_Phytochemicals.tsv",
    "therapeutic_uses": "IMPPAT_TherapeuticUse_Plant_Association.tsv",
    "single_formulations": "IMPPAT_SingleHerbalFormulations.tsv",
    "poly_formulations": "IMPPAT_PolyHerbalFormulations.tsv",
}


# --------------------------------------------------
# TSV READER
# --------------------------------------------------

def read_tsv(filename):
    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Missing dataset: {path}")

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        return list(csv.DictReader(file, delimiter="\t"))


def save_record(file, record):
    file.write(
        json.dumps(record, ensure_ascii=False) + "\n"
    )


def clean(value):
    return str(value or "").strip()


def contains_turmeric(value):
    value = clean(value).lower()
    return "curcuma longa" in value


# --------------------------------------------------
# LOAD DATASETS
# --------------------------------------------------

def load_datasets():
    print("Loading IMPPAT datasets...")

    return {
        key: read_tsv(filename)
        for key, filename in FILES.items()
    }


# --------------------------------------------------
# PROCESS TURMERIC RECORDS
# --------------------------------------------------

def process():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    data = load_datasets()

    plant_rows = [
        row for row in data["plants"]
        if clean(row.get("Plant_identifier")) == PLANT_ID
    ]

    if not plant_rows:
        raise ValueError(
            "Curcuma longa plant record not found."
        )

    plant = plant_rows[0]

    # Identify phytochemical associations.
    associations = [
        row for row in data["plant_chemicals"]
        if clean(row.get("Plant_identifier")) == PLANT_ID
    ]

    # Group plant-part and reference information.
    compound_details = defaultdict(
        lambda: {
            "plant_parts": set(),
            "references": set()
        }
    )

    for row in associations:
        compound_id = clean(
            row.get("IMPPAT_Phytochemical_identifier")
        )

        if not compound_id:
            continue

        if clean(row.get("Plant_part")):
            compound_details[compound_id]["plant_parts"].add(
                clean(row["Plant_part"])
            )

        if clean(row.get("Reference_identifier")):
            compound_details[compound_id]["references"].add(
                clean(row["Reference_identifier"])
            )

    compound_ids = set(compound_details.keys())

    chemicals = {
        clean(row.get("IMPPAT_Phytochemical_identifier")): row
        for row in data["chemicals"]
        if clean(row.get("IMPPAT_Phytochemical_identifier"))
        in compound_ids
    }

    bioactivity = [
        row for row in data["bioactivity"]
        if clean(row.get("IMPPAT_Phytochemical_identifier"))
        in compound_ids
    ]

    therapeutic_uses = [
        row for row in data["therapeutic_uses"]
        if clean(row.get("IMPPAT_Plant_identifier")) == PLANT_ID
    ]

    single_formulations = [
        row for row in data["single_formulations"]
        if contains_turmeric(row.get("Plant_name_standardised"))
    ]

    poly_formulations = [
        row for row in data["poly_formulations"]
        if contains_turmeric(row.get("Plant_name_standardised"))
    ]

    # --------------------------------------------------
    # WRITE SEARCHABLE RECORDS
    # --------------------------------------------------

    counts = defaultdict(int)

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as output:

        # 1. Plant profile
        plant_text = (
            f"Medicinal plant: {PLANT_NAME}. "
            f"Common name: {clean(plant.get('Common_name'))}. "
            f"Family: {clean(plant.get('Family'))}. "
            f"Synonyms: {clean(plant.get('Synonymous names'))}. "
            f"Systems of medicine: "
            f"{clean(plant.get('System_of_Medicine'))}."
        )

        save_record(output, {
            "id": f"IMPPAT_PLANT_{PLANT_ID}",
            "text": plant_text,
            "metadata": {
                "document_type": "plant_profile",
                "source": "IMPPAT",
                "plant_name": PLANT_NAME,
                "plant_id": PLANT_ID,
                "family": clean(plant.get("Family")),
                "language": "en"
            }
        })

        counts["plant_profile"] += 1

        # 2. Phytochemical records
        for compound_id, details in compound_details.items():

            chemical = chemicals.get(compound_id, {})

            name = clean(
                chemical.get("Phytochemical name_standardised")
            )

            if not name:
                name = compound_id

            text = (
                f"Phytochemical associated with {PLANT_NAME}: "
                f"{name}. "
                f"Phytochemical identifier: {compound_id}. "
                f"Plant parts: "
                f"{', '.join(sorted(details['plant_parts']))}. "
                f"Synonyms: "
                f"{clean(chemical.get('Synonymous chemical names'))}. "
                f"Functional groups: "
                f"{clean(chemical.get('Functional_Groups'))}. "
                f"References: "
                f"{', '.join(sorted(details['references']))}."
            )

            save_record(output, {
                "id": f"IMPPAT_CHEM_{compound_id}",
                "text": text,
                "metadata": {
                    "document_type": "phytochemical",
                    "source": "IMPPAT",
                    "plant_name": PLANT_NAME,
                    "plant_id": PLANT_ID,
                    "phytochemical_id": compound_id,
                    "phytochemical_name": name,
                    "plant_parts": ", ".join(
                        sorted(details["plant_parts"])
                    ),
                    "language": "en"
                }
            })

            counts["phytochemical"] += 1

        # 3. Bioactivity observations
        for index, row in enumerate(bioactivity):

            compound_id = clean(
                row.get("IMPPAT_Phytochemical_identifier")
            )

            chemical = chemicals.get(compound_id, {})

            compound_name = clean(
                chemical.get("Phytochemical name_standardised")
            ) or compound_id

            measurements = []

            for field in ["EC50", "IC50", "Kd", "Ki"]:
                value = clean(row.get(field))

                if value:
                    measurements.append(f"{field}: {value}")

            text = (
                f"Bioactivity record for phytochemical "
                f"{compound_name}, associated with {PLANT_NAME}. "
                f"Target: {clean(row.get('Target_name'))}. "
                f"Target organism: "
                f"{clean(row.get('Target_organism'))}. "
                f"Measurements: {'; '.join(measurements)}. "
                f"Source database: {clean(row.get('Source'))}."
            )

            save_record(output, {
                "id": f"IMPPAT_BIO_{compound_id}_{index}",
                "text": text,
                "metadata": {
                    "document_type": "bioactivity",
                    "source": "IMPPAT",
                    "plant_name": PLANT_NAME,
                    "plant_id": PLANT_ID,
                    "phytochemical_id": compound_id,
                    "phytochemical_name": compound_name,
                    "target": clean(row.get("Target_name")),
                    "target_organism": clean(
                        row.get("Target_organism")
                    ),
                    "source_database": clean(row.get("Source")),
                    "language": "en"
                }
            })

            counts["bioactivity"] += 1

        # 4. Therapeutic-use associations
        for index, row in enumerate(therapeutic_uses):

            use = clean(row.get("Therapeutic_use"))

            text = (
                f"IMPPAT therapeutic-use association for "
                f"{PLANT_NAME}. "
                f"Plant part: {clean(row.get('Plant_part'))}. "
                f"Associated therapeutic-use term: {use}. "
                f"Record identifier: "
                f"{clean(row.get('IMPPAT_Therapeutic_use_identifier'))}. "
                f"This is a database association, not proof "
                f"of clinical efficacy."
            )

            save_record(output, {
                "id": f"IMPPAT_USE_{index}",
                "text": text,
                "metadata": {
                    "document_type": "traditional_use_reference",
                    "source": "IMPPAT",
                    "plant_name": PLANT_NAME,
                    "plant_id": PLANT_ID,
                    "therapeutic_use": use,
                    "plant_part": clean(row.get("Plant_part")),
                    "language": "en"
                }
            })

            counts["therapeutic_use"] += 1

        # 5. Single-herbal formulations
        for index, row in enumerate(single_formulations):

            text = (
                f"Single-herbal formulation associated with "
                f"{PLANT_NAME}. "
                f"Formulation: "
                f"{clean(row.get('Formulation_name_in_API_original'))}. "
                f"Ingredient: "
                f"{clean(row.get('Ingredient name in API_original'))}. "
                f"Plant part: "
                f"{clean(row.get('Plant part in API_original'))}. "
                f"Therapeutic uses as listed in API: "
                f"{clean(row.get('Therapeutic_uses (according to The Ayurvedic Pharmacopoeia of India)'))}. "
                f"References: {clean(row.get('References'))}."
            )

            save_record(output, {
                "id": f"IMPPAT_SINGLE_{index}",
                "text": text,
                "metadata": {
                    "document_type": "single_herbal_formulation",
                    "source": "IMPPAT",
                    "plant_name": PLANT_NAME,
                    "formulation_id": clean(
                        row.get("Formulation_identifier")
                    ),
                    "language": "en"
                }
            })

            counts["single_formulation"] += 1

        # 6. Polyherbal formulation ingredient records
        for index, row in enumerate(poly_formulations):

            text = (
                f"Polyherbal formulation ingredient record. "
                f"Formulation: "
                f"{clean(row.get('Formulation name_in_AFI_original'))}. "
                f"Turmeric ingredient: "
                f"{clean(row.get('Ingredient name in AFI_original'))}. "
                f"Standardized plant: "
                f"{clean(row.get('Plant_name_standardised'))}. "
                f"Plant part: "
                f"{clean(row.get('Plant_part_standardised'))}. "
                f"Other formulation information: "
                f"{clean(row.get('Therapeutic uses (according to The Ayurvedic Formulary of India)') )}. "
                f"References: {clean(row.get('References'))}."
            )

            save_record(output, {
                "id": f"IMPPAT_POLY_{index}",
                "text": text,
                "metadata": {
                    "document_type": "polyherbal_formulation",
                    "source": "IMPPAT",
                    "plant_name": PLANT_NAME,
                    "formulation_id": clean(
                        row.get("Formulation_identifier")
                    ),
                    "ingredient": clean(
                        row.get("Ingredient_name_standardised")
                    ),
                    "language": "en"
                }
            })

            counts["polyherbal_formulation"] += 1

    # --------------------------------------------------
    # SUMMARY
    # --------------------------------------------------

    unique_poly_formulations = {
        clean(row.get("Formulation_identifier"))
        for row in poly_formulations
        if clean(row.get("Formulation_identifier"))
    }

    print("\n========== IMPPAT PROCESSING COMPLETE ==========")
    print("Plant:", PLANT_NAME)
    print("Plant ID:", PLANT_ID)

    for category, count in counts.items():
        print(f"{category}: {count}")

    print(
        "Unique polyherbal formulations:",
        len(unique_poly_formulations)
    )

    print("Total searchable records:", sum(counts.values()))
    print("Output:", OUTPUT_FILE)


if __name__ == "__main__":
    process()
