from sqlalchemy import Column, String, CheckConstraint
from sqlalchemy.orm import relationship, Session
from backend.app.database import Base

class College(Base):
    """Global dimension table for TVET Colleges and training institutions.
    Maintains a global surrogate key (C0001, C0002...) across the entire document corpus.
    """
    __tablename__ = "colleges"

    college_id = Column(String, primary_key=True)
    college_name = Column(String, nullable=False, unique=True)
    data_quality_flag = Column(String, nullable=True)
    data_quality_note = Column(String, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "data_quality_flag IS NULL OR data_quality_flag IN ('review_possible_variant')",
            name="chk_college_quality_flag",
        ),
    )

    qualification_links = relationship(
        "QualificationCollege",
        back_populates="college",
        cascade="all, delete-orphan",
    )
    dspp_links = relationship(
        "DsppCentreOfSpecialisation",
        back_populates="college",
        cascade="all, delete-orphan",
    )

    GENERIC_STOPWORDS = {
        "college",
        "colleges",
        "tvet",
        "tvet college",
        "tvet colleges",
        "participating",
        "participating colleges",
        "participating tvet colleges",
        "none",
        "nil",
        "n/a",
        "na",
        "no",
        "-",
        "--",
    }

    @classmethod
    def get_or_create(cls, db: Session, college_name: str, quality_flag: str = None, quality_note: str = None) -> "College | None":
        """Get existing college by exact name match or create with the next global surrogate key.
        Returns None if college_name is a generic stopword.
        """
        if not college_name:
            return None

        clean_name = college_name.strip()
        if len(clean_name) < 3 or clean_name.lower() in cls.GENERIC_STOPWORDS:
            return None

        # 1. Check in-memory pending objects in session
        for obj in db.new:
            if isinstance(obj, cls) and obj.college_name.strip().lower() == clean_name.lower():
                return obj

        # 2. Check existing committed/flushed in database
        existing = db.query(cls).filter(cls.college_name == clean_name).first()
        if existing:
            return existing

        # 3. Determine next global surrogate ID (C0001, C0002...)
        max_num = 0
        existing_ids = db.query(cls.college_id).all()
        for (cid,) in existing_ids:
            if cid and cid.startswith("C") and cid[1:].isdigit():
                max_num = max(max_num, int(cid[1:]))

        for obj in db.new:
            if isinstance(obj, cls) and obj.college_id and obj.college_id.startswith("C") and obj.college_id[1:].isdigit():
                max_num = max(max_num, int(obj.college_id[1:]))

        new_id = f"C{max_num + 1:04d}"
        college = cls(
            college_id=new_id,
            college_name=clean_name,
            data_quality_flag=quality_flag,
            data_quality_note=quality_note,
        )
        db.add(college)
        db.flush()
        return college
