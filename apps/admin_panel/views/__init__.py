from .academic_cycle_create_view import academic_cycle_create_view
from .academic_cycle_edit_view import academic_cycle_edit_view
from .academic_cycle_list_view import academic_cycle_list_view
from .academic_term_create_view import academic_term_create_view
from .academic_term_edit_view import academic_term_edit_view
from .academic_year_create_view import academic_year_create_view
from .academic_year_edit_view import academic_year_edit_view
from .academic_year_list_view import academic_year_list_view
from .backup_view import backup_download_view, backup_list_view
from .course_grading_formula_view import course_grading_formula_view
from .data_subject_export_view import (
    data_subject_export_guardian_view,
    data_subject_export_student_view,
    data_subject_export_view,
)
from .grading_formula_config_view import grading_formula_config_view
from .institution_config_view import institution_config_view
from .institution_edit_view import institution_edit_view
from .non_teaching_day_create_view import non_teaching_day_create_view
from .non_teaching_day_edit_view import non_teaching_day_edit_view
from .non_teaching_day_list_view import non_teaching_day_list_view
from .schedule_occupancy_view import schedule_occupancy_view
from .subject_grading_formula_view import subject_grading_formula_view
from .user_create_view import user_create_view
from .user_edit_view import user_edit_view
from .user_list_view import user_list_view

__all__ = [
    "academic_cycle_create_view",
    "academic_cycle_edit_view",
    "academic_cycle_list_view",
    "academic_term_create_view",
    "academic_term_edit_view",
    "academic_year_create_view",
    "academic_year_edit_view",
    "academic_year_list_view",
    "backup_download_view",
    "backup_list_view",
    "course_grading_formula_view",
    "data_subject_export_guardian_view",
    "data_subject_export_student_view",
    "data_subject_export_view",
    "grading_formula_config_view",
    "institution_config_view",
    "institution_edit_view",
    "non_teaching_day_create_view",
    "non_teaching_day_edit_view",
    "non_teaching_day_list_view",
    "schedule_occupancy_view",
    "subject_grading_formula_view",
    "user_create_view",
    "user_edit_view",
    "user_list_view",
]
