# 미용사(일반) 필기 문제풀이 웹앱

기출문제 PDF와 예상문제 PDF를 JSON으로 변환해 만든 정적 웹앱입니다.  
백엔드 없이 `HTML + CSS + JavaScript + JSON`만 사용합니다.

## 수록 내용

| 구분 | 회차 | 문제 수 |
|------|------|--------|
| 기출문제 | 2010-07-11, 2010-10-03, 2011-04-17, 2011-07-31, 2011-10-09 | 300문제 |
| 예상문제 | 2026 예상문제 4~9 (무니쌤 미용교실) | 360문제 |
| **합계** | **11개 회차** | **660문제** |

## 주요 기능

- 회차별 문제풀이 선택
- 문제 1개씩 순차 풀이
- 선택 즉시 정답/오답 피드백
- 풀이 완료 후 점수 및 오답 목록 표시
- 원본 PDF 링크 제공 (그림 선택지 문제)

## 파일 구조

```
hair_written_quiz_app/
├─ index.html
├─ app.js
├─ styles.css
├─ data/
│  ├─ questions.json        # 전체 문제 데이터
│  └─ extract-report.json
├─ pdfs/
│  ├─ 20100711.pdf ~ 20111009.pdf   # 기출문제 5개
│  ├─ latest60.pdf                  # 예상문제 7
│  └─ munissam-expected4~9.pdf      # 예상문제 4~9
└─ scripts/
   └─ extract-pdf-questions.py      # PDF → JSON 추출 스크립트
```

## 로컬 실행

```bash
python -m http.server 5173
```

브라우저에서 `http://localhost:5173` 접속

## 배포 (Cloudflare Pages)

빌드 과정 없는 정적 사이트입니다.

- Framework preset: `None`
- Build command: 비워두기
- Build output directory: `/`

GitHub 저장소 연결 후 즉시 배포됩니다.

## 새 문제 추가 방법

1. PDF 파일을 `pdfs/` 폴더에 추가
2. `data/questions.json`의 `rounds` 배열에 회차 정보 추가
3. `questions` 배열에 문제 데이터 추가
4. `totalQuestions` 값 업데이트
