# ConnectBox 최종발표 테스트 체크리스트

## 자동 테스트

- [ ] `python -m py_compile ...` 컴파일 PASS
- [ ] `python scripts\smoke_test_local.py ...` 단일 파일 PASS
- [ ] `python scripts\smoke_test_multi_files.py ...` 다중 파일 PASS
- [ ] `python scripts\smoke_test_folder.py ...` 폴더 전송 PASS
- [ ] `logs/`에 실패 로그가 남는지 확인

## CLI 기능

- [ ] 서버 실행: `python -m server.server_main --host 127.0.0.1 --port 5001`
- [ ] 단일 파일 전송
- [ ] 여러 파일 전송
- [ ] 폴더 전송
- [ ] 중복 파일명이 있으면 `_1`, `_2` suffix로 보존
- [ ] 폴더 내부 구조가 `received/` 아래에 복원

## GUI 기능

- [ ] `python -m gui.connectbox_gui` 실행
- [ ] 받기 모드에서 Host/Port/저장 폴더 입력 가능
- [ ] 받기 서버 시작 가능
- [ ] 보내기 모드에서 서버 IP/Port 입력 가능
- [ ] 파일 선택 가능
- [ ] 여러 파일 선택 가능
- [ ] 폴더 선택 가능
- [ ] 현재 파일 진행률 표시
- [ ] 전체 진행률 표시
- [ ] 상태 로그 표시
- [ ] 전송 완료 후 버튼이 다시 활성화

## LAN 시연

- [ ] 두 PC가 같은 LAN에 연결됨
- [ ] 서버 PC IPv4 주소 확인
- [ ] 서버 GUI 또는 CLI가 Host `0.0.0.0`으로 실행됨
- [ ] 클라이언트가 서버 PC IPv4로 접속
- [ ] Windows 방화벽 허용 확인
- [ ] 수신 폴더에 파일 생성 확인

## 패키징

- [ ] 패키징 PC에서 `python -m pip install pyinstaller`
- [ ] `python scripts\build_exe.py --target gui`
- [ ] `python scripts\build_exe.py --target client`
- [ ] `python scripts\build_exe.py --target server`
- [ ] `dist/` 결과물 생성 확인
- [ ] `dist/`, `build/`, `*.spec`가 Git에 포함되지 않음

## Git 상태

- [ ] 코드/문서 변경만 추적됨
- [ ] `logs/`, `received/`, `testdata/`, `build/`, `dist/` 산출물이 추적되지 않음
