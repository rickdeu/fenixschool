"""Dados de demonstração para o ambiente de desenvolvimento local.

Pedido explícito do utilizador: o utilizador `root` (criado por
`accounts.management.commands.create_dev_superuser`, também guardado por
`settings.DEBUG`) deve sempre ter, logo após uma instalação nova ou um
`migrate`, dados suficientes para simular quase todo o sistema -- uma
instituição completa, com utilizadores de cada perfil, estrutura curricular,
uma turma com pelo menos 50 alunos matriculados, horário, notas lançadas e
médias calculadas.

Este módulo (e o comando de gestão que o invoca,
`apps.core.management.commands.seed_demo_data`) nunca corre fora de
`DEBUG=True` -- mesma garantia que `create_dev_superuser` já tem, e pela
mesma razão: nunca inventar dados falsos numa instituição real em produção.
Idempotente: verifica se a instituição de demonstração já existe antes de
criar seja o que for, para poder correr em segurança em todo `docker compose
up`/`migrate`, não só na primeira vez.
"""

import random
from datetime import date, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction

from apps.academic.models import (
    Course,
    CurricularYear,
    Department,
    Room,
    Schedule,
    SchoolClass,
    Subject,
)
from apps.accounts.models import Profile, User
from apps.core.context import get_current_node_id, tenant_context
from apps.core.models import AcademicCycle, AcademicTerm, AcademicYear, IdentificationDocumentType
from apps.core.services import setup_institution
from apps.enrollment.models import Candidate, Guardian, Student, StudentGuardian
from apps.enrollment.services import enroll_student, register_student
from apps.grading.models import EvaluationType, Grade
from apps.grading.services import registar_media_final

DEMO_INSTITUTION_NAME = "Escola Demo FenixSchool"
DEMO_PASSWORD = "Demo@1234"
DEMO_STUDENT_COUNT = 55
# Namespaced ("-DEMO") so it can never collide with a code a real
# institution already uses, when seeding into one that already existed on
# this node instead of a brand new one.
DEMO_SCHOOL_CLASS_CODE = "10A-DEMO"

_FIRST_NAMES = [
    "Ana",
    "Bento",
    "Cesária",
    "Domingos",
    "Esperança",
    "Fernando",
    "Graça",
    "Hélder",
    "Isabel",
    "João",
    "Kianda",
    "Luzia",
    "Manuel",
    "Nzinga",
    "Osvaldo",
    "Paula",
    "Quintino",
    "Rosa",
    "Sebastião",
    "Teresa",
    "Ussumane",
    "Vitória",
    "Wanda",
    "Xavier",
    "Yara",
    "Zeferino",
]
_LAST_NAMES = [
    "Alberto",
    "Bumba",
    "Chissano",
    "Domingos",
    "Estevão",
    "Fernandes",
    "Gonçalves",
    "Hango",
    "Inácio",
    "João",
    "Kiala",
    "Lopes",
    "Muteka",
    "Neto",
    "Osório",
    "Pascoal",
    "Quifica",
    "Ribeiro",
    "Sequeira",
    "Tomás",
]


def _random_name(rng: random.Random) -> tuple[str, str]:
    return rng.choice(_FIRST_NAMES), rng.choice(_LAST_NAMES)


def _origin():
    return get_current_node_id()


def seed_demo_data() -> bool:
    """Idempotent entry point: returns `False` (no-op) if this node already
    has the demo turma seeded, `True` if it just created everything. Only
    ever does anything when `settings.DEBUG` is `True`.

    Seeds into whichever `Institution` this node already has (creating one
    via `setup_institution` only if there's truly none yet) instead of
    always creating a brand new, separately named one:
    `apps.core.middleware.TenantMiddleware`'s own fallback for a Super
    Administrador with no institution "picker" UI (not built yet) is
    `Institution.objects.first()` -- a second, competing institution here
    would just never be the one `root` (or any other Super Administrador)
    actually lands on. Local nodes are single-tenant by design
    (docs/04-arquitetura-tecnica.md §4.4.1) -- there should only ever be one
    anyway.
    """
    if not settings.DEBUG:
        return False

    from apps.core.models import Institution

    institution = Institution.objects.first()
    if institution is not None:
        with tenant_context(institution.id):
            if SchoolClass.objects.filter(code=DEMO_SCHOOL_CLASS_CODE).exists():
                return False
        with transaction.atomic():
            _seed(random.Random(2026), institution)
        return True

    with transaction.atomic():
        institution, _manager = setup_institution(
            institution_data={"name": DEMO_INSTITUTION_NAME, "tax_id": "5401234567"},
            manager_data={
                "username": "admin.demo",
                "first_name": "Administradora",
                "last_name": "Demo",
                "email": "admin.demo@escola-demo.ao",
                "password": DEMO_PASSWORD,
            },
        )
        _seed(random.Random(2026), institution)
    return True


def _seed(rng: random.Random, institution) -> None:
    # `root` (issue accounts.create_dev_superuser) is only useful as a demo
    # tour guide if it's actually looking at this institution's data --
    # ordinary (non-Super-Admin) views scope by the logged-in user's own
    # `institution`.
    User.objects.filter(username="root").update(institution=institution)

    with tenant_context(institution.id):
        origin_node_id = _origin()

        # -- Utilizadores de cada perfil (issue #113/§7.1) -------------------
        User.objects.create_user(
            username="direcao.demo",
            institution=institution,
            profile=Profile.PEDAGOGICAL_DIRECTION,
            first_name="Direção",
            last_name="Pedagógica",
            email="direcao.demo@escola-demo.ao",
            password=DEMO_PASSWORD,
        )
        User.objects.create_user(
            username="secretaria.demo",
            institution=institution,
            profile=Profile.SECRETARY,
            first_name="Secretaria",
            last_name="Escolar",
            email="secretaria.demo@escola-demo.ao",
            password=DEMO_PASSWORD,
        )
        User.objects.create_user(
            username="financeiro.demo",
            institution=institution,
            profile=Profile.FINANCE,
            first_name="Financeiro",
            last_name="Demo",
            email="financeiro.demo@escola-demo.ao",
            password=DEMO_PASSWORD,
        )
        User.objects.create_user(
            username="rh.demo",
            institution=institution,
            profile=Profile.HR,
            first_name="Recursos",
            last_name="Humanos",
            email="rh.demo@escola-demo.ao",
            password=DEMO_PASSWORD,
        )
        User.objects.create_user(
            username="biblioteca.demo",
            institution=institution,
            profile=Profile.LIBRARY,
            first_name="Biblioteca",
            last_name="Demo",
            email="biblioteca.demo@escola-demo.ao",
            password=DEMO_PASSWORD,
        )
        User.objects.create_user(
            username="aluno.demo",
            institution=institution,
            profile=Profile.STUDENT,
            first_name="Aluno",
            last_name="Demo",
            email="aluno.demo@escola-demo.ao",
            password=DEMO_PASSWORD,
        )
        teacher_matematica = User.objects.create_user(
            username="professor.matematica.demo",
            institution=institution,
            profile=Profile.TEACHER,
            first_name="Professor",
            last_name="Matemática",
            email="professor.matematica.demo@escola-demo.ao",
            password=DEMO_PASSWORD,
        )
        teacher_diretor_turma = User.objects.create_user(
            username="diretor.turma.demo",
            institution=institution,
            profile=Profile.HOMEROOM_TEACHER,
            first_name="Diretora",
            last_name="de Turma",
            email="diretor.turma.demo@escola-demo.ao",
            password=DEMO_PASSWORD,
        )

        # -- Estrutura curricular (docs/05-modelo-de-dados.md §5.4-5.9) -----
        document_type = IdentificationDocumentType.objects.get(code="bilhete-de-identidade")
        department = Department.objects.create(
            institution=institution, origin_node_id=origin_node_id, name="Ciências e Letras (Demo)"
        )
        cycle = AcademicCycle.objects.create(
            institution=institution,
            origin_node_id=origin_node_id,
            designation="2.º Ciclo do Ensino Secundário (Demo)",
            order=1,
        )
        course = Course.objects.create(
            institution=institution,
            origin_node_id=origin_node_id,
            code="CTEC-DEMO",
            name="Ciências Físicas e Biológicas (Demo)",
            created_on=date(2020, 1, 1),
            department=department,
            cycle=cycle,
            duration_years=3,
        )
        curricular_year_10 = CurricularYear.objects.create(
            institution=institution,
            origin_node_id=origin_node_id,
            course=course,
            number=1,
            equivalent_grade="10.ª classe",
        )
        curricular_year_11 = CurricularYear.objects.create(
            institution=institution,
            origin_node_id=origin_node_id,
            course=course,
            number=2,
            equivalent_grade="11.ª classe",
        )

        subjects_10 = {
            name: Subject.objects.create(
                institution=institution,
                origin_node_id=origin_node_id,
                code=code,
                name=name,
                created_on=date(2020, 1, 1),
                course=course,
                curricular_year=curricular_year_10,
                cycle=cycle,
                subject_type=Subject.SubjectType.MANDATORY,
                weekly_hours=4,
            )
            for code, name in (
                ("MAT10-DEMO", "Matemática"),
                ("POR10-DEMO", "Português"),
                ("FIS10-DEMO", "Física"),
                ("HIS10-DEMO", "História"),
            )
        }
        subjects_11 = {
            name: Subject.objects.create(
                institution=institution,
                origin_node_id=origin_node_id,
                code=code,
                name=name,
                created_on=date(2020, 1, 1),
                course=course,
                curricular_year=curricular_year_11,
                cycle=cycle,
                subject_type=Subject.SubjectType.MANDATORY,
                weekly_hours=4,
            )
            for code, name in (("MAT11-DEMO", "Matemática"), ("POR11-DEMO", "Português"))
        }

        academic_year = AcademicYear.objects.create(
            institution=institution,
            origin_node_id=origin_node_id,
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
            is_current=True,
        )
        term_1 = AcademicTerm.objects.create(
            institution=institution,
            origin_node_id=origin_node_id,
            academic_year=academic_year,
            number=1,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 5, 15),
        )
        AcademicTerm.objects.create(
            institution=institution,
            origin_node_id=origin_node_id,
            academic_year=academic_year,
            number=2,
            start_date=date(2026, 5, 16),
            end_date=date(2026, 8, 31),
        )
        AcademicTerm.objects.create(
            institution=institution,
            origin_node_id=origin_node_id,
            academic_year=academic_year,
            number=3,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 15),
        )

        room_1 = Room.objects.create(
            institution=institution,
            origin_node_id=origin_node_id,
            designation="Sala 1 (Demo)",
            capacity=60,
        )
        room_2 = Room.objects.create(
            institution=institution,
            origin_node_id=origin_node_id,
            designation="Sala 2 (Demo)",
            capacity=40,
        )

        school_class_10a = SchoolClass.objects.create(
            institution=institution,
            origin_node_id=origin_node_id,
            code=DEMO_SCHOOL_CLASS_CODE,
            designation="10.ª A (Demo)",
            academic_year=academic_year,
            course=course,
            curricular_year=curricular_year_10,
            max_enrollment=max(DEMO_STUDENT_COUNT + 5, 60),
            shift=SchoolClass.Shift.MORNING,
        )
        school_class_11a = SchoolClass.objects.create(
            institution=institution,
            origin_node_id=origin_node_id,
            code="11A-DEMO",
            designation="11.ª A (Demo)",
            academic_year=academic_year,
            course=course,
            curricular_year=curricular_year_11,
            max_enrollment=40,
            shift=SchoolClass.Shift.AFTERNOON,
        )

        # -- Horário (issue #36) ---------------------------------------------
        Schedule.objects.create(
            institution=institution,
            origin_node_id=origin_node_id,
            school_class=school_class_10a,
            subject=subjects_10["Matemática"],
            weekday=Schedule.Weekday.MONDAY,
            start_time=time(8, 0),
            end_time=time(9, 30),
            regime=Schedule.Regime.THEORETICAL,
            room=room_1,
            teacher=teacher_matematica,
        )
        Schedule.objects.create(
            institution=institution,
            origin_node_id=origin_node_id,
            school_class=school_class_10a,
            subject=subjects_10["Português"],
            weekday=Schedule.Weekday.TUESDAY,
            start_time=time(8, 0),
            end_time=time(9, 30),
            regime=Schedule.Regime.THEORETICAL,
            room=room_1,
            teacher=teacher_diretor_turma,
        )
        Schedule.objects.create(
            institution=institution,
            origin_node_id=origin_node_id,
            school_class=school_class_11a,
            subject=subjects_11["Matemática"],
            weekday=Schedule.Weekday.WEDNESDAY,
            start_time=time(13, 30),
            end_time=time(15, 0),
            regime=Schedule.Regime.THEORETICAL,
            room=room_2,
            teacher=teacher_matematica,
        )

        # -- Candidatos (pré-inscrição, issue #42) ---------------------------
        for i in range(1, 4):
            first, last = _random_name(rng)
            Candidate.objects.create(
                institution=institution,
                origin_node_id=origin_node_id,
                full_name=f"{first} {last}",
                birth_date=date(2011, 1, 1) + timedelta(days=i * 30),
                document_type=document_type,
                document_number=f"DEMO-CAND-{i:04d}",
                document_expiry_date=date(2032, 1, 1),
                desired_course=course,
                contact=f"9{i:08d}",
            )

        # -- Alunos, encarregados, matrículas (issues #39-#46) --------------
        evaluation_types = list(EvaluationType.objects.filter(institution=institution))

        def _enroll_class(school_class, curricular_year, subjects, count, code_prefix):
            for i in range(1, count + 1):
                first, last = _random_name(rng)
                birth_date = date(2026, 1, 1) - timedelta(days=rng.randint(15 * 365, 17 * 365))
                guardian_first, guardian_last = _random_name(rng)
                guardian = Guardian.objects.create(
                    institution=institution,
                    origin_node_id=origin_node_id,
                    full_name=f"{guardian_first} {guardian_last}",
                    kinship=rng.choice([Guardian.Kinship.MOTHER, Guardian.Kinship.FATHER]),
                    document_type=document_type,
                    document_number=f"DEMO-ENC-{code_prefix}-{i:04d}",
                    mobile_phone=f"9{i:08d}",
                )
                student = register_student(
                    institution=institution,
                    document_type=document_type,
                    document_number=f"DEMO-AL-{code_prefix}-{i:04d}",
                    guardian_consent_given_by=guardian,
                    origin_node_id=origin_node_id,
                    first_name=first,
                    last_name=last,
                    birth_date=birth_date,
                    gender=rng.choice([Student.Gender.MALE, Student.Gender.FEMALE]),
                    document_issue_date=date(2023, 1, 1),
                    document_issue_place="Nacional - Luanda",
                )
                StudentGuardian.objects.create(
                    institution=institution,
                    origin_node_id=origin_node_id,
                    student=student,
                    guardian=guardian,
                    is_primary=True,
                    financially_responsible=True,
                )
                enrollment = enroll_student(
                    institution=institution,
                    student=student,
                    school_class=school_class,
                    origin_node_id=origin_node_id,
                    course=course,
                    academic_year=academic_year,
                    cycle=cycle,
                    curricular_year=curricular_year,
                    presented_document_type=document_type,
                    presented_document_number=student.document_number,
                    document_issue_date=date(2023, 1, 1),
                    document_issue_place="Nacional - Luanda",
                )
                yield student, enrollment, guardian

        demo_10a = list(
            _enroll_class(
                school_class_10a, curricular_year_10, subjects_10, DEMO_STUDENT_COUNT, "10A"
            )
        )
        # Consumed only to force the enrolment loop to actually run --
        # generator function, lazy otherwise -- the 11.ª A roster itself
        # isn't needed afterwards (no notas seeded for it, see below).
        list(_enroll_class(school_class_11a, curricular_year_11, subjects_11, 12, "11A"))

        # One Guardian gets real portal access, to demo `guardian_portal`.
        _, _, first_guardian = demo_10a[0]
        guardian_user = User.objects.create_user(
            username="encarregado.demo",
            institution=institution,
            profile=Profile.GUARDIAN,
            first_name="Encarregado",
            last_name="Demo",
            email="encarregado.demo@escola-demo.ao",
            password=DEMO_PASSWORD,
        )
        first_guardian.user = guardian_user
        first_guardian.save(update_fields=["user"])

        # -- Notas e médias (issues #55-#58), só na turma grande, 1.º período
        subject_teachers = {
            subjects_10["Matemática"]: teacher_matematica,
            subjects_10["Português"]: teacher_diretor_turma,
        }
        for subject, teacher in subject_teachers.items():
            for student, enrollment, _guardian in demo_10a:
                for evaluation_type in evaluation_types:
                    Grade.objects.create(
                        institution=institution,
                        origin_node_id=origin_node_id,
                        student=student,
                        enrollment=enrollment,
                        subject=subject,
                        academic_term=term_1,
                        evaluation_type=evaluation_type,
                        value=Decimal(rng.randint(60, 200)) / Decimal(10),
                        teacher=teacher,
                    )
                registar_media_final(
                    enrollment=enrollment,
                    subject=subject,
                    academic_term=term_1,
                    origin_node_id=origin_node_id,
                )
