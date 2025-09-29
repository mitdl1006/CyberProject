# Markdown Styler

마크다운 문서를 실시간으로 디자인하고, 꾸민 그대로 PDF로 내보낼 수 있는 Django 기반 웹 애플리케이션입니다. 상단 팔레트에서 색상, 폰트, 여백, 그림자 등을 조절하면 미리보기와 PDF 출력에 즉시 반영됩니다.

## 주요 기능

- ✏️ 마크다운 에디터: 실시간 문법 하이라이팅과 미리보기
- 🎨 디자인 팔레트: 배경/텍스트/포인트 색상, 목록 스타일, 카드 그림자 등을 즉시 변경
- 📄 PDF 출력: WeasyPrint 기반으로 디자인이 적용된 PDF 생성
- ⚡ 빠른 피드백: 서버 렌더링 기반 프리뷰 API & 프론트엔드 디바운싱으로 부드러운 사용자 경험

## 기술 스택

- Django 5.x
- markdown-it-py (마크다운 → HTML 변환)
- WeasyPrint (HTML → PDF 렌더링)
- Vanilla JS + CSS (팔레트 & 실시간 프리뷰 UI)
- uv (Python 패키지 및 실행 관리)

## 빠른 시작

```pwsh
# 의존성 설치 (이미 설치되어 있다면 생략)
uv sync

# 데이터베이스 초기화 (필요 시)
uv run manage.py migrate

# 개발 서버 실행 (루트에서 main.py 실행)
uv run main.py

# 또는 manage.py를 직접 사용하고 싶다면
cd mysite
uv run manage.py runserver 0.0.0.0:8000
```

## 사용 가이드

1. 브라우저에서 `http://127.0.0.1:8000/` 접속
2. 좌측 팔레트에서 문서 제목과 스타일을 설정
3. 가운데 편집기에 마크다운 입력
4. 우측 미리보기에서 결과 확인
5. 상단 `PDF 다운로드` 버튼으로 출력물 저장

## 테스트

```pwsh
uv run manage.py test editor
```

## 라이선스

이 저장소는 MIT License를 따릅니다.
