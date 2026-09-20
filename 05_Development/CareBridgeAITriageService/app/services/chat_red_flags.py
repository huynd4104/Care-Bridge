"""Deterministic red-flag screen for AI Nurse chat messages (BR-SAFETY safety floor).

Used when retrieval finds no document: the grounding gate must never silently answer an emergency
with a generic refusal and has_critical_warning=False. The screen works on accent-stripped text so
messages typed without Vietnamese diacritics ("mau ra o at") are caught too.

Design choices:
- Recall over precision: no negation handling (naive negation stripping caused a past triage bug).
- Pure information-seeking questions ("dấu hiệu nguy hiểm là gì?") that do not describe the asker's
  own situation are not flagged.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import List, Optional

RED_FLAG_SELF_HARM = "SELF_HARM"
RED_FLAG_NEWBORN = "NEWBORN"
RED_FLAG_OBSTETRIC = "OBSTETRIC"


def strip_diacritics(text: str) -> str:
    """Lowercase, remove Vietnamese diacritics (đ -> d) and collapse whitespace."""
    s = unicodedata.normalize("NFD", (text or "").lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.replace("đ", "d")
    return re.sub(r"\s+", " ", s).strip()


# Patterns operate on strip_diacritics() output.
_SELF_HARM_PATTERNS = (
    r"\btu tu\b", r"\btu sat\b", r"lam hai ban than", r"tu lam hai", r"tu gay hai", r"lam dau ban than",
    r"khong muon song", r"\bmuon chet\b", r"ket thuc cuoc doi", r"bien mat cho xong",
    r"y nghi (tu )?(lam hai|gay hai|tu tu)",
    r"cau (so )?10\b.{0,80}(hiem khi|thinh thoang|kha thuong xuyen|thuong xuyen|[123] diem)",
)

_NEWBORN_SUBJECT = r"\b(be|tre|con|so sinh)\b"
_NEWBORN_SIGNS = (
    r"vang da", r"(mat|long ban tay|long ban chan)\b.{0,30}\bvang\b", r"\bvang\b.{0,30}\b(mat|long ban tay|long ban chan)\b",
    r"bu kem", r"bo bu", r"khong (chiu )?bu", r"tho ren", r"tim tai", r"kho tho",
    r"co giat", r"mem nhe[o]?", r"\bsot\b", r"nong (ran|hau|qua)",
)

_OBSTETRIC_PATTERNS = (
    r"ra mau", r"chay mau", r"bang huyet", r"mau (ra|chay) (o at|nhieu|tuoi)", r"uot (dam|het) bang",
    r"vo oi", r"ri oi", r"(ri|chay|ra) nuoc (o |tu )?(am dao|duoi|vung kin)",
    r"co giat", r"ngat xiu", r"\bngat\b", r"bat tinh", r"lo mo",
    r"dau bung (du doi|quan|nhieu|du lam)", r"dau quan",
    r"dau dau (du doi|du lam|nhieu)", r"nhin mo", r"mo mat", r"dom sang", r"hoa mat",
    r"dau (vung )?(thuong vi|duoi mui uc|ha suon)",
    r"phu (mat|mi mat|dot ngot)", r"khong thao (duoc )?nhan",
    r"(thai|con|be)\b.{0,20}(dap it|it dap|khong dap|khong thay dap|ngung dap|im han|khong (thay )?(cu dong|may))",
    r"(dap|may) (it|yeu) (han|hon)",
    r"(chi|moi) (dap|cu dong|thay dap|thay cu dong)( duoc)? [0-3] (lan|cai)",
    r"khong (thay )?(be |con |thai )?(dap|cu dong|may) nua", r"\bim han\b", r"cuong loan",
    r"san dich (co mui )?hoi", r"sot cao",
    r"kho tho", r"dau nguc",
)

_BP_PATTERN = re.compile(r"(huyet ap|\bha\b|\bbp\b|mmhg).{0,30}?(\d{2,3})\s*/\s*(\d{2,3})|(\d{2,3})\s*/\s*(\d{2,3})\s*mmhg")
_FEVER_PATTERN = re.compile(r"(\b(3[89]|4[0-2])(?:[.,]\d)?)\s*(do|°|oc)\b")

_INFO_SEEKING = re.compile(
    r"(la gi|nhung dau hieu|cac dau hieu|dau hieu nao|khi nao can|cach nhan biet|nhu the nao la|"
    r"the nao la|bao gom nhung|gom nhung gi|quy tac|quy trinh|huong dan)"
)
_PERSONAL_SITUATION = re.compile(
    r"\b(em|toi|minh|vo toi|vo em|con em|con toi|be nha|con dau|chau toi|me bau nha)\b|"
    r"\b(dang bi|vua bi|bi \w+|sinh duoc|bau \d+|mang thai \d+|thai \d+ tuan)\b"
)


@dataclass(frozen=True)
class RedFlagResult:
    category: str
    matched: str


def _first_match(patterns, text: str) -> Optional[str]:
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return m.group(0)
    return None


def _severe_bp(text: str) -> Optional[str]:
    for m in _BP_PATTERN.finditer(text):
        sys_s, dia_s = (m.group(2), m.group(3)) if m.group(2) else (m.group(4), m.group(5))
        systolic, diastolic = int(sys_s), int(dia_s)
        if systolic >= 160 or diastolic >= 110:
            return m.group(0)
    return None


def detect_red_flags(message: str) -> List[RedFlagResult]:
    """Return red flags found in a chat message (empty list when none)."""
    text = strip_diacritics(message)
    if not text:
        return []

    if not _PERSONAL_SITUATION.search(text):
        # Drop only the sentences that are general knowledge questions ("dấu hiệu nguy hiểm là gì?");
        # a danger sign stated in another sentence ("Khi nào cần đi viện? Thai không máy nữa") still counts.
        sentences = [s for s in re.split(r"[?.!;\n]+", text) if s.strip()]
        text = " ".join(s for s in sentences if not _INFO_SEEKING.search(s)).strip()
        if not text:
            return []

    found: List[RedFlagResult] = []
    hit = _first_match(_SELF_HARM_PATTERNS, text)
    if hit:
        found.append(RedFlagResult(RED_FLAG_SELF_HARM, hit))

    if re.search(_NEWBORN_SUBJECT, text):
        hit = _first_match(_NEWBORN_SIGNS, text)
        if hit and re.search(r"(so sinh|moi sinh|vua sinh|sinh duoc|ngay tuoi|tieng|gio tuoi|\d+ ngay)", text):
            found.append(RedFlagResult(RED_FLAG_NEWBORN, hit))

    hit = _first_match(_OBSTETRIC_PATTERNS, text) or _severe_bp(text)
    if not hit:
        fever = _FEVER_PATTERN.search(text)
        if fever and re.search(r"(sau sinh|sinh duoc|moi sinh|san dich|dang bau|mang thai|bau)", text):
            hit = fever.group(0)
    if hit:
        found.append(RedFlagResult(RED_FLAG_OBSTETRIC, hit))
    return found


# An answer to an emergency must tell the user to get care now; these are the phrasings that do (on
# strip_diacritics() output). Negated uses ("không cần cấp cứu", "chưa phải đi viện") are removed first.
_URGENT_REFERRAL = re.compile(
    # Only calls to action: "đây là dấu hiệu cấp cứu" alone names the danger without telling what to do.
    r"\b115\b|goi cap cuu|cap cuu ngay|kham cap cuu|den ngay|toi ngay|di kham ngay|kham ngay|di vien ngay|"
    r"nhap vien|(den|toi|vao|dua .{0,30}(den|toi|vao)) (benh vien|vien|co so y te|phong kham|khoa cap cuu)"
)
_NEGATED_REFERRAL = re.compile(r"\b(khong|chua|chang)( can| phai)+\b[^.;:!?\n]{0,30}")


def contains_urgent_referral(answer: str) -> bool:
    """True when the answer text itself tells the user to seek care urgently."""
    text = _NEGATED_REFERRAL.sub(" ", strip_diacritics(answer))
    return _URGENT_REFERRAL.search(text) is not None
