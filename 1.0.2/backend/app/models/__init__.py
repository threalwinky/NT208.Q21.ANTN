from app.models.advisor import (
    AcademicRiskSnapshot,
    CoursePrerequisite,
    DegreeCourse,
    DegreeProgram,
    ProgramCourseRequirement,
    SemesterPlan,
    SemesterPlanItem,
    StudentAcademicProfile,
    StudentCourseRecord,
)
from app.models.academic import AcademicEvent, ClassSchedule, ExamSchedule, Reminder, Task
from app.models.chat import ChatMessage, ChatSession
from app.models.knowledge import (
    Announcement,
    CollectedDocument,
    ContentCategory,
    ContentCategoryCode,
    ConfidenceLevel,
    CrawlerLog,
    CrawlStatus,
    DataSource,
    Department,
    DocumentChunk,
    FAQ,
    SourceType,
    SupportResource,
)
from app.models.users import StudentProfile, User, UserRole
from app.models.wellbeing import (
    InAppNotification,
    MoodJournal,
    MoodState,
    SavedAnnouncement,
    SystemConfig,
)
