"""호칭어/지칭어(및 고유명사) 치환 사전 관리.

- CSV로 영구 저장(%APPDATA%\\Cortuni\\terms.csv)
- 프로그램을 처음 실행할 때 자주 쓰이는 한국어 호칭/지칭어를 기본으로 채워 둔다
  (바꿀 단어는 우선 원래 단어와 동일하게 넣어두고, 사용자가 원하는 값으로 고쳐 쓰면 된다).
- 각 항목은 "작품(그룹)"을 가질 수 있다. 그룹이 비어 있으면 "공통"으로 취급되어
  어떤 작품을 선택하든 항상 적용되고, 그룹이 있으면 그 작품을 선택했을 때만 적용된다.
"""

import csv
import os

APP_DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Cortuni")
DICT_PATH = os.path.join(APP_DATA_DIR, "terms.csv")

CSV_FIELDS = ["원래단어", "바꿀단어", "작품"]

# 자주 쓰이는 한국어 호칭/지칭어 기본 목록.
# (바꿀단어는 원래단어와 동일하게 시작 -> 사용자가 필요한 것만 값을 고쳐 쓰면 됨)
_DEFAULT_WORDS = [
    "형", "오빠", "언니", "누나", "동생", "남동생", "여동생",
    "형아", "누나야", "언니야", "오빠야",
    "아빠", "엄마", "아버지", "어머니",
    "할아버지", "할머니", "외할아버지", "외할머니",
    "삼촌", "외삼촌", "고모", "고모부", "이모", "이모부",
    "사촌", "사촌형", "사촌오빠", "사촌언니", "사촌누나", "사촌동생", "조카",
    "아들", "딸", "손자", "손녀",
    "남편", "아내", "와이프", "신랑", "신부",
    "장인", "장모", "시아버지", "시어머니", "며느리", "사위",
    "처남", "처형", "처제", "동서", "매형", "매부", "형부", "제부",
    "선생님", "교수님", "사장님", "대표님", "회장님", "부장님", "과장님",
    "대리님", "팀장님", "이사님", "실장님", "원장님",
    "선배", "후배", "사부", "스승님", "제자",
    "아저씨", "아주머니", "아줌마", "아가씨", "총각", "어르신",
    "자기야", "여보", "당신",
    "폐하", "전하", "각하", "마마", "왕자님", "공주님", "도련님",
]

COMMON_GROUP = ""  # 그룹이 비어 있으면 "공통"


def default_entries():
    return [{"원래단어": w, "바꿀단어": w, "작품": COMMON_GROUP} for w in _DEFAULT_WORDS]


class TermDict:
    def __init__(self, path=None):
        self.path = path or DICT_PATH
        self.entries = []
        self.load_or_seed()

    def load_or_seed(self):
        if os.path.isfile(self.path):
            self.entries = self._read_csv(self.path)
        else:
            self.entries = default_entries()
            self.save()

    def _read_csv(self, path, encoding="utf-8-sig"):
        entries = []
        with open(path, newline="", encoding=encoding) as f:
            reader = csv.DictReader(f)
            for row in reader:
                old = (row.get("원래단어") or "").strip()
                new = (row.get("바꿀단어") or "").strip()
                group = (row.get("작품") or "").strip()
                if not old:
                    continue
                entries.append({"원래단어": old, "바꿀단어": new or old, "작품": group})
        return entries

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for e in self.entries:
                writer.writerow(e)

    def groups(self):
        """공통(빈 문자열)을 제외한, 등록된 작품 그룹 이름 목록(중복 제거, 정렬)."""
        return sorted({e["작품"] for e in self.entries if e["작품"]})

    def add(self, old, new, group=""):
        old = old.strip()
        new = new.strip() or old
        group = group.strip()
        if not old:
            return
        for e in self.entries:
            if e["원래단어"] == old and e["작품"] == group:
                e["바꿀단어"] = new
                self.save()
                return
        self.entries.append({"원래단어": old, "바꿀단어": new, "작품": group})
        self.save()

    def delete(self, indices):
        """entries 리스트 인덱스들(여러 개 가능)을 삭제."""
        keep = [e for i, e in enumerate(self.entries) if i not in set(indices)]
        self.entries = keep
        self.save()

    def import_csv(self, path):
        """외부 CSV를 불러와 (원래단어, 작품) 기준으로 추가/갱신한다. 불러온 행 수를 반환."""
        try:
            new_rows = self._read_csv(path, encoding="utf-8-sig")
        except UnicodeDecodeError:
            new_rows = self._read_csv(path, encoding="cp949")

        count = 0
        for row in new_rows:
            self.add(row["원래단어"], row["바꿀단어"], row["작품"])
            count += 1
        return count

    def active_mapping(self, selected_groups):
        """공통 항목 + 선택된 작품 그룹 항목을 합쳐 {원래단어: 바꿀단어} 딕셔너리로 반환.

        같은 원래단어가 공통과 작품 그룹에 모두 있으면 작품 그룹 쪽이 우선한다.
        """
        selected = set(selected_groups or [])
        mapping = {}
        for e in self.entries:
            if e["작품"] == COMMON_GROUP:
                mapping[e["원래단어"]] = e["바꿀단어"]
        for e in self.entries:
            if e["작품"] in selected:
                mapping[e["원래단어"]] = e["바꿀단어"]
        return {k: v for k, v in mapping.items() if k != v}
