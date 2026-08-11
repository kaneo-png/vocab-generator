"""試験マスタとドメインルールの初期データ投入。"""
from app.extensions import db
from app.models.exam import Exam, ExamDomainRule


EXAMS = [
    {"name": "TOEIC", "description": "ビジネス英語中心の試験。Part5-7で語彙力が問われる。"},
    {"name": "英検準1級", "description": "大学中級レベル。時事・社会問題・学術的な語彙が中心。"},
    {"name": "IELTS", "description": "海外留学・移住用。アカデミック語彙と一般語彙のバランス。"},
    {"name": "英検1級", "description": "大学上級レベル。人文・社会・自然科学の高度な語彙。"},
]

# 各試験のドメインルール（人手の知見を注入）
DOMAIN_RULES = {
    "TOEIC": [
        {"rule_type": "exclude", "category": "war", "description": "軍事・戦争関連語はTOEICではほぼ出ない"},
        {"rule_type": "exclude", "category": "religion", "description": "宗教関連語はTOEICではほぼ出ない"},
        {"rule_type": "prioritize", "category": "business", "description": "ビジネス・契約・物流はTOEIC頻出"},
        {"rule_type": "prioritize", "category": "finance", "description": "財務・会計用語はTOEIC Part7で頻出"},
        {"rule_type": "prioritize", "category": "hr", "description": "人事・採用関連はTOEIC Part7で頻出"},
    ],
    "英検準1級": [
        {"rule_type": "prioritize", "category": "social_issues", "description": "社会問題（環境・貧困・教育）が頻出"},
        {"rule_type": "prioritize", "category": "academic", "description": "学術語彙が長文読解で頻出"},
        {"rule_type": "prioritize", "category": "politics", "description": "政治・国際関係は時事問題で頻出"},
    ],
    "IELTS": [
        {"rule_type": "prioritize", "category": "academic", "description": "アカデミック語彙がReading/Writingで必須"},
        {"rule_type": "prioritize", "category": "environment", "description": "環境問題はIELTS定番トピック"},
        {"rule_type": "prioritize", "category": "education", "description": "教育関連はIELTS定番トピック"},
    ],
    "英検1級": [
        {"rule_type": "prioritize", "category": "humanities", "description": "人文科学（哲学・文学）の語彙が頻出"},
        {"rule_type": "prioritize", "category": "science", "description": "自然科学の専門用語が頻出"},
        {"rule_type": "prioritize", "category": "social_issues", "description": "社会問題の高度な議論で使用"},
    ],
}


def seed_exams() -> None:
    """試験マスタとドメインルールを投入する（冪等）。"""
    for exam_data in EXAMS:
        exam = Exam.query.filter_by(name=exam_data["name"]).first()
        if not exam:
            exam = Exam(name=exam_data["name"], description=exam_data["description"])
            db.session.add(exam)
            db.session.flush()
        elif not exam.description:
            exam.description = exam_data["description"]

        # ドメインルール投入
        for rule_data in DOMAIN_RULES.get(exam.name, []):
            exists = ExamDomainRule.query.filter_by(
                exam_id=exam.id,
                rule_type=rule_data["rule_type"],
                category=rule_data["category"],
            ).first()
            if not exists:
                db.session.add(ExamDomainRule(
                    exam_id=exam.id,
                    rule_type=rule_data["rule_type"],
                    category=rule_data["category"],
                    description=rule_data["description"],
                ))

    db.session.commit()
