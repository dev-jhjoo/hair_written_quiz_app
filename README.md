# 미용사(일반) 필기 문제풀이 웹앱

첨부된 5개 회차 PDF를 `questions.json`으로 변환해서 만든 정적 웹앱입니다.
백엔드 없이 `HTML + CSS + JavaScript + JSON`만 사용합니다.

## 포함 내용

- 5개 회차
- 총 300문제
- 문제 1개씩 풀이
- 4지선다 선택
- 선택 즉시 정답/오답 표시
- 다음 문제 이동
- 마지막 점수 표시
- 회차별 풀이 또는 전체 풀이
- 원본 PDF 링크 제공

## 파일 구조

```txt
hair_written_quiz_app/
├─ index.html
├─ app.js
├─ styles.css
├─ data/
│  ├─ questions.json
│  └─ extract-report.json
├─ pdfs/
│  ├─ 20100711.pdf
│  ├─ 20101003.pdf
│  ├─ 20110417.pdf
│  ├─ 20110731.pdf
│  └─ 20111009.pdf
└─ scripts/
   └─ extract-pdf-questions.py
```

## 로컬 실행

정적 파일이므로 아래 중 하나로 실행하면 됩니다.

```bash
python -m http.server 5173
```

브라우저에서 다음 주소로 접속합니다.

```txt
http://localhost:5173
```

## Cloudflare Pages 배포

빌드 과정이 없는 정적 사이트입니다.

- Framework preset: None
- Build command: 비워두기
- Build output directory: `/` 또는 프로젝트 루트

GitHub에 이 폴더를 올린 뒤 Cloudflare Pages에서 저장소를 연결하면 됩니다.

## 추출 참고사항

`2010-10-03` 회차의 1번 문제는 선택지가 그림 형태로 들어 있어 텍스트 추출이 되지 않았습니다.
앱에서는 해당 문제에 원본 PDF 확인 안내를 표시합니다.
