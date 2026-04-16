import re
import logging

class PiiMasker:
    # HIRD-G: 治理层，负责对进入模型的数据进行 PII 脱敏，确保合规与隐私。

    # 简单的 PII 模式定义
    PHONE_PATTERN = re.compile(r'1[3-9]\d{9}')
    ID_CARD_PATTERN = re.compile(r'\d{17}[\dxX]|\d{15}')
    # 姓名识别通常需要更复杂的 NLP，此处用简单模式占位，实际生产会用 NER 模型
    NAME_PLACEHOLDER = "[NAME]"

    @classmethod
    def mask_text(cls, text: str) -> str:
        if not text:
            return text

        masked = text
        # 1. 脱敏手机号
        masked = cls.PHONE_PATTERN.sub("[PHONE]", masked)
        # 2. 脱敏身份证号
        masked = cls.ID_CARD_PATTERN.sub("[ID_CARD]", masked)

        # 3. 记录日志（不包含明文）
        if masked != text:
            logging.info("PII information masked in text.")

        return masked

    @classmethod
    def is_pii_masked(cls, text: str) -> bool:
        return "[PHONE]" in text or "[ID_CARD]" in text or "[NAME]" in text
