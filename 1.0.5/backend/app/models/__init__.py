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
from app.models.academic import AcademicEvent, ClassSchedule, ExamSchedule, Reminder, StudyPlan, StudyPlanCourse, StudyPlanSemester, Task
from app.models.chat import ChatMessage, ChatSession
from app.models.feedback import UserFeedback
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
    StructuredFactType,
    StructuredKnowledgeFact,
    SupportResource,
)
from app.models.users import StudentProfile, User, UserRole
from app.models.wellbeing import (
    InAppNotification,
    MoodCheckin,
    MoodJournal,
    MoodState,
    MusicPlaylist,
    SavedAnnouncement,
    SpotifyAccount,
    SpotifyPlaylistMapping,
    SystemConfig,
    WellbeingNote,
    WellbeingRecommendation,
)
