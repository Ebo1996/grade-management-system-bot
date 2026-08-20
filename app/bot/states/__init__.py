"""FSM state groups."""
from app.bot.states.result_upload import ResultUploadStates
from app.bot.states.admin_states import AddTeacherStates, AddStudentStates

__all__ = ["ResultUploadStates", "AddTeacherStates", "AddStudentStates"]
