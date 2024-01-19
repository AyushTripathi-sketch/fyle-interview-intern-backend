import enum
from core import db
from core.apis.decorators import AuthPrincipal
from core.libs import helpers, assertions
from core.models.teachers import Teacher
from core.models.students import Student
from sqlalchemy.types import Enum as BaseEnum


class GradeEnum(str, enum.Enum):
    A = 'A'
    B = 'B'
    C = 'C'
    D = 'D'


class AssignmentStateEnum(str, enum.Enum):
    DRAFT = 'DRAFT'
    SUBMITTED = 'SUBMITTED'
    GRADED = 'GRADED'


class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, db.Sequence('assignments_id_seq'), primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey(Student.id), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey(Teacher.id), nullable=True)
    content = db.Column(db.Text)
    grade = db.Column(BaseEnum(GradeEnum))
    state = db.Column(BaseEnum(AssignmentStateEnum), default=AssignmentStateEnum.DRAFT, nullable=False)
    created_at = db.Column(db.TIMESTAMP(timezone=True), default=helpers.get_utc_now, nullable=False)
    updated_at = db.Column(db.TIMESTAMP(timezone=True), default=helpers.get_utc_now, nullable=False, onupdate=helpers.get_utc_now)

    def __repr__(self):
        return '<Assignment %r>' % self.id

    @classmethod
    def filter(cls, *criterion):
        db_query = db.session.query(cls)
        return db_query.filter(*criterion)

    @classmethod
    def get_by_id(cls, _id):
        return cls.filter(cls.id == _id).first()

    @classmethod
    def upsert(cls, assignment_new: 'Assignment'):
        if assignment_new.id is not None:
            assignment = Assignment.get_by_id(assignment_new.id)
            assertions.assert_found(assignment, 'No assignment with this id was found')
            assertions.assert_valid(assignment.state == AssignmentStateEnum.DRAFT,
                                    'only assignment in draft state can be edited')

            assignment.content = assignment_new.content
        else:
            assignment = assignment_new
            assertions.assert_valid(assignment.content is not None, "content cannot be null")
            db.session.add(assignment_new)

        db.session.flush()
        return assignment

    @classmethod
    def submit(cls, _id, teacher_id, auth_principal: AuthPrincipal):
        assignment = Assignment.get_by_id(_id)
        assertions.assert_found(assignment, 'No assignment with this id was found')
        assertions.assert_valid(assignment.student_id == auth_principal.student_id, 'This assignment belongs to some other student')
        assertions.assert_valid(assignment.content is not None, 'assignment with empty content cannot be submitted')
        # print(assignment.state == AssignmentStateEnum.DRAFT)
        assertions.assert_valid(assignment.state == AssignmentStateEnum.DRAFT, 'only a draft assignment can be submitted')

        assignment.teacher_id = teacher_id
        assignment.state = AssignmentStateEnum.SUBMITTED
        db.session.flush()

        return assignment


    @classmethod
    def mark_grade(cls, _id, grade, auth_principal: AuthPrincipal):
        assignment = Assignment.get_by_id(_id)
        assertions.assert_found(assignment, 'No assignment with this id was found')
        if auth_principal.teacher_id:
            assertions.assert_valid(assignment.teacher_id == auth_principal.teacher_id)
        assertions.assert_valid(assignment.state != AssignmentStateEnum.DRAFT,"Cannot grade a draft assignment")
        print("sssdasd")
        assertions.assert_valid(grade is not None, 'assignment with empty grade cannot be graded')

        assignment.grade = grade
        assignment.state = AssignmentStateEnum.GRADED
        db.session.flush()

        return assignment

    @classmethod
    def get_assignments_by_student(cls, student_id):
        return cls.filter(cls.student_id == student_id).all()

    @classmethod
    def get_assignments_by_teacher(cls, teacher_id):
        return cls.filter(cls.teacher_id == teacher_id).all()

    @classmethod
    def get_submitted_and_graded_assignments(cls):
        """
        Returns:
            List[Assignment]: List of submitted and graded assignments.
        """
        return cls.filter(
            (cls.state == AssignmentStateEnum.SUBMITTED) | (cls.state == AssignmentStateEnum.GRADED)
        ).all()

    @classmethod
    def delete_by_id(cls, _id):
        """
        Deletes an assignment based on its ID.

        Args:
            _id (int): The ID of the assignment to delete.

        Returns:
            bool: True if the assignment was successfully deleted, False otherwise.
        """
        assignment = cls.get_by_id(_id)
        if assignment:
            db.session.delete(assignment)
            db.session.commit()
            return True
        return False

    @classmethod
    def get_assignment_counts_by_state(cls):
        """
        Gets the number of assignments for each state.

        Returns:
            dict: A dictionary where keys are assignment states (e.g., 'DRAFT', 'SUBMITTED', 'GRADED')
                  and values are the corresponding counts.
        """
        states_count = db.session.query(cls.state, db.func.count(cls.id)).group_by(cls.state).all()
        return [(state.value, count) for state, count in states_count]

    @classmethod
    def get_max_graded_teacher_count_for_grade_A(cls):
        """
        Gets the count of grade A assignments for the teacher who has graded the maximum number of assignments.

        Returns:
            int: The count of grade A assignments for the teacher with the maximum graded assignments.
        """
        max_graded_teacher_id = db.session.query(cls.teacher_id, db.func.count(cls.id)).filter(
            cls.state == AssignmentStateEnum.GRADED
        ).group_by(cls.teacher_id).order_by(db.func.count(cls.id).desc()).first()

        if max_graded_teacher_id:
            max_teacher_id, _ = max_graded_teacher_id
            grade_A_count = db.session.query(db.func.count(cls.id)).filter(
                cls.teacher_id == max_teacher_id,
                cls.grade == GradeEnum.A
            ).scalar()
            return grade_A_count

        return 0