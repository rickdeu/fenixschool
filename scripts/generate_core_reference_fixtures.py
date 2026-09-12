"""Generate the `core` app's national reference-data fixtures.

Produces the four JSON fixture files backing issue #11 (Criar fixtures de
referência nacional): `provinces_municipalities.json`, `mobile_operators.json`,
`document_types.json` and `professions.json`, written to `apps/core/fixtures/`.
The source data is kept here, in one place, rather than typed twice between
this script and the JSON it emits.

Re-run with `python scripts/generate_core_reference_fixtures.py` whenever the
reference data needs to be regenerated (e.g. a new municipality, a spelling
fix). It only rewrites the fixture files; it does not touch the database.

Provinces reflect Angola's current division (21 provinces, Lei 14/24 de 5 de
Setembro de 2024), which split the old Luanda, Cuando Cubango and Moxico
provinces into six: Luanda/Ícolo e Bengo, Cuando/Cubango and Moxico/Moxico
Leste. Municipalities for the fifteen provinces the reform left untouched are
still at the pre-reform level of detail; the six split provinces use the
post-reform municipality lists where a reliable source (Wikipedia, cross
-checked) was available. Angola's own post-reform municipality count is much
higher nationwide (~326, many former communes elevated to municipality
status) than what is listed here (~185) -- this dataset should be revisited
once an authoritative source (INE / official gazette) for the remaining
fifteen provinces' new municipalities is available.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FIXTURES_DIR = BASE_DIR / "apps" / "core" / "fixtures"


def slugify(value: str) -> str:
    """ASCII, hyphen-separated code derived from a Portuguese display name."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return "-".join(re.split(r"[^a-zA-Z0-9]+", ascii_only.lower())).strip("-")


PROVINCES_MUNICIPALITIES: dict[str, list[str]] = {
    "Bengo": [
        "Ambriz",
        "Bula Atumba",
        "Dande",
        "Dembos",
        "Nambuangongo",
        "Pango Aluquém",
    ],
    "Benguela": [
        "Baía Farta",
        "Balombo",
        "Benguela",
        "Bocoio",
        "Caimbambo",
        "Catumbela",
        "Chongoroi",
        "Cubal",
        "Ganda",
        "Lobito",
    ],
    "Bié": [
        "Andulo",
        "Camacupa",
        "Catabola",
        "Chinguar",
        "Chitembo",
        "Cuemba",
        "Cunhinga",
        "Kuito",
        "Nharea",
    ],
    "Cabinda": ["Belize", "Buco-Zau", "Cabinda", "Cacongo"],
    # Split from the old "Cuando Cubango" province by Lei 14/24 (2024).
    "Cuando": [
        "Cuito Cuanavale",
        "Dima",
        "Dirico",
        "Luengue",
        "Luiana",
        "Mavinga",
        "Mucusso",
        "Rivungo",
        "Xipundo",
    ],
    "Cubango": [
        "Caiundo",
        "Calai",
        "Chinguanja",
        "Cuangar",
        "Cuchi",
        "Cutato",
        "Longa",
        "Mavengue",
        "Menongue",
        "Nancova",
        "Savate",
    ],
    "Cuanza Norte": [
        "Ambaca",
        "Banga",
        "Bolongongo",
        "Cambambe",
        "Cazengo",
        "Golungo Alto",
        "Gonguembo",
        "Lucala",
        "Quiculungo",
        "Samba Caju",
    ],
    "Cuanza Sul": [
        "Amboim",
        "Cassongue",
        "Cela",
        "Conda",
        "Ebo",
        "Libolo",
        "Mussende",
        "Porto Amboim",
        "Quibala",
        "Quilenda",
        "Seles",
        "Sumbe",
    ],
    "Cunene": [
        "Cahama",
        "Cuanhama",
        "Curoca",
        "Cuvelai",
        "Namacunde",
        "Ombadja",
    ],
    "Huambo": [
        "Bailundo",
        "Caála",
        "Catchiungo",
        "Chicala-Cholohanga",
        "Ecunha",
        "Huambo",
        "Londuimbali",
        "Longonjo",
        "Mungo",
        "Tchindjenje",
        "Ucuma",
    ],
    "Huíla": [
        "Caconda",
        "Cacula",
        "Caluquembe",
        "Chibia",
        "Chicomba",
        "Chipindo",
        "Cuvango",
        "Gambos",
        "Humpata",
        "Jamba",
        "Lubango",
        "Matala",
        "Quilengues",
        "Quipungo",
    ],
    # Split from Luanda by Lei 14/24 (2024) -- the new province's own
    # municipalities (Bom Jesus, Cabiri, Cabo Ledo, Calumbo, Catete, Quiçama,
    # Sequele), not the old Luanda-province ones.
    "Ícolo e Bengo": [
        "Bom Jesus",
        "Cabiri",
        "Cabo Ledo",
        "Calumbo",
        "Catete",
        "Quiçama",
        "Sequele",
    ],
    # Reduced by Lei 14/24 (2024): the municipalities that moved to Ícolo e
    # Bengo (Belas' rural area, Icolo e Bengo, Quiçama) are no longer here.
    "Luanda": [
        "Belas",
        "Cacuaco",
        "Cazenga",
        "Kilamba Kiaxi",
        "Luanda",
        "Talatona",
        "Viana",
    ],
    "Lunda Norte": [
        "Cambulo",
        "Capenda-Camulemba",
        "Caungula",
        "Chitato",
        "Cuango",
        "Cuílo",
        "Lóvua",
        "Lubalo",
        "Lucapa",
        "Xá-Muteba",
    ],
    "Lunda Sul": ["Cacolo", "Dala", "Muconda", "Saurimo"],
    "Malanje": [
        "Cacuso",
        "Calandula",
        "Cambundi-Catembo",
        "Cangandala",
        "Caombo",
        "Cuaba Nzogo",
        "Cunda-Dia-Baze",
        "Luquembo",
        "Malanje",
        "Marimba",
        "Massango",
        "Mucari",
        "Quela",
        "Quirima",
    ],
    # Reduced by Lei 14/24 (2024): the eastern municipalities moved to Moxico
    # Leste below.
    "Moxico": ["Bundas", "Camanongue", "Léua", "Luchazes", "Moxico"],
    # Split from Moxico by Lei 14/24 (2024).
    "Moxico Leste": [
        "Caianda",
        "Cameia",
        "Cazombo",
        "Lago Dilolo",
        "Lóvua do Zambeze",
        "Luacano",
        "Luau",
        "Macondo",
        "Nana Candundo",
    ],
    "Namibe": ["Bibala", "Camucuio", "Namibe", "Tômbwa", "Virei"],
    "Uíge": [
        "Alto Cauale",
        "Ambuíla",
        "Bembe",
        "Buengas",
        "Bungo",
        "Cangola",
        "Damba",
        "Mucaba",
        "Negage",
        "Puri",
        "Quimbele",
        "Quitexe",
        "Sanza Pombo",
        "Songo",
        "Uíge",
        "Zombo",
    ],
    "Zaire": ["Cuimba", "Mbanza Kongo", "Nóqui", "Nzeto", "Soyo", "Tomboco"],
}

MOBILE_OPERATORS: list[str] = ["Unitel", "Movicel", "Africell"]

DOCUMENT_TYPES: list[str] = [
    "Bilhete de Identidade",
    "Cédula Pessoal",
    "Passaporte",
    "Assento de Nascimento",
]

# Simplified national classification of professions (CNP simplificada) --
# covers the `profession` field used when registering a guardian or a
# working student (docs/05-modelo-de-dados.md, linha 200). Also includes
# common non-occupational states used in that same field (student,
# unemployed, retired).
PROFESSIONS: list[str] = [
    "Advogado(a)",
    "Agricultor(a)",
    "Arquiteto(a)",
    "Bancário(a)",
    "Cabeleireiro(a)",
    "Carpinteiro(a)",
    "Comerciante",
    "Contabilista",
    "Costureiro(a)",
    "Cozinheiro(a)",
    "Desempregado(a)",
    "Doméstico(a)",
    "Economista",
    "Eletricista",
    "Empresário(a)",
    "Enfermeiro(a)",
    "Engenheiro(a)",
    "Estudante",
    "Farmacêutico(a)",
    "Funcionário(a) Público(a)",
    "Gestor(a)",
    "Jornalista",
    "Mecânico(a)",
    "Médico(a)",
    "Militar",
    "Ministro(a) de Culto Religioso",
    "Motorista",
    "Pedreiro(a)",
    "Pescador(a)",
    "Pintor(a)",
    "Polícia",
    "Professor(a)",
    "Psicólogo(a)",
    "Reformado(a)",
    "Segurança",
    "Serralheiro(a)",
    "Soldador(a)",
    "Técnico(a) Administrativo(a)",
    "Técnico(a) de Enfermagem",
    "Técnico(a) de Informática",
    "Tradutor(a)/Intérprete",
    "Vendedor(a) Ambulante",
    "Veterinário(a)",
    "Outra",
]


def build_provinces_municipalities_fixture() -> list[dict]:
    records = []
    for province_name, municipalities in PROVINCES_MUNICIPALITIES.items():
        province_code = slugify(province_name)
        records.append(
            {
                "model": "core.province",
                "pk": province_code,
                "fields": {"name": province_name},
            }
        )
        for municipality_name in municipalities:
            municipality_code = f"{province_code}-{slugify(municipality_name)}"
            records.append(
                {
                    "model": "core.municipality",
                    "pk": municipality_code,
                    "fields": {
                        "name": municipality_name,
                        "province": province_code,
                    },
                }
            )
    return records


def build_simple_fixture(model_name: str, names: list[str]) -> list[dict]:
    return [
        {
            "model": f"core.{model_name}",
            "pk": slugify(name),
            "fields": {"name": name},
        }
        for name in names
    ]


def write_fixture(filename: str, records: list[dict]) -> None:
    path = FIXTURES_DIR / filename
    path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(records)} records to {path.relative_to(BASE_DIR)}")


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    write_fixture("provinces_municipalities.json", build_provinces_municipalities_fixture())
    write_fixture(
        "mobile_operators.json",
        build_simple_fixture("mobileoperator", MOBILE_OPERATORS),
    )
    write_fixture(
        "document_types.json",
        build_simple_fixture("identificationdocumenttype", DOCUMENT_TYPES),
    )
    write_fixture("professions.json", build_simple_fixture("profession", PROFESSIONS))


if __name__ == "__main__":
    main()
