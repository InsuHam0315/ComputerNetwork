# ConnectBox

ConnectBox는 같은 PC 또는 같은 LAN 안의 Windows PC 사이에서 TCP socket으로
파일을 직접 전송하는 컴퓨터네트워크 과목 프로젝트입니다.

최종발표 버전은 중간발표 MVP의 CLI 단일 파일 전송을 유지하면서, 프로토콜 v2
기반 다중 파일 전송, 폴더 전송, 폴더 구조 복원, Tkinter GUI, 자동 테스트,
Windows 실행파일 패키징 준비를 추가했습니다.

## 주요 기능

- Python 표준 라이브러리 기반 TCP 파일 전송
- 기존 단일 파일 전송 유지: `FILE_SEND / READY / COMPLETE / ERROR`
- 새 전송 세션(v2)
  - 여러 파일 전송
  - 폴더 재귀 전송
  - `relative_path` 기반 폴더 구조 복원
  - 파일별 진행률과 전체 진행률
- CLI 실행 지원
- Tkinter GUI
  - 받기 모드
  - 보내기 모드
  - 서버 IP/포트 입력
  - 파일 선택, 여러 파일 선택, 폴더 선택
  - 현재 파일/전체 진행률
  - 상태 로그
- 자동 smoke test
  - 단일 파일
  - 다중 파일
  - 폴더 구조 복원
- PyInstaller 기반 Windows exe 패키징 스크립트

## 프로젝트 구조

```text
client/
  client_main.py          # CLI 송신 + GUI가 호출하는 송신 core
server/
  server_main.py          # CLI 수신 + GUI가 호출하는 수신 core
common/
  protocol.py             # v1/v2 메타데이터 프로토콜 유틸
  progress.py             # 진행률/바이트 표시 유틸
gui/
  connectbox_gui.py       # Tkinter GUI
scripts/
  create_dummy_file.py
  smoke_test_local.py
  smoke_test_multi_files.py
  smoke_test_folder.py
  build_exe.py
docs/
  demo_plan.md
  testing.md
  test_checklist.md
실행방법.txt
```

`build/`, `dist/`, `logs/`, `received/`, `testdata/`는 실행/테스트 산출물이므로
Git에 포함하지 않습니다.

## 프로토콜

모든 메타데이터는 다음 형식으로 전송합니다.

```text
4-byte big-endian JSON length
UTF-8 JSON metadata
```

### v1: 단일 파일 호환 프로토콜

중간발표 MVP와 호환되는 단일 파일 전송 흐름입니다.

```text
client -> server: FILE_SEND {filename, filesize}
server -> client: RESPONSE READY
client -> server: file body bytes
server -> client: RESPONSE COMPLETE 또는 ERROR
```

### v2: 전송 세션 프로토콜

다중 파일/폴더 전송에 사용하는 세션 흐름입니다.

```text
client -> server: TRANSFER_START {version, item_count, total_size}
server -> client: RESPONSE READY

반복:
client -> server: FILE_ITEM {index, filename, relative_path, filesize}
server -> client: RESPONSE READY
client -> server: file body bytes
server -> client: FILE_DONE {index, status}

client -> server: TRANSFER_END {version, item_count, total_size}
server -> client: RESPONSE COMPLETE 또는 ERROR
```

폴더 전송 시 클라이언트는 선택한 폴더 이름을 포함한 `relative_path`를 보내고,
서버는 이를 저장 폴더 아래에 안전하게 복원합니다. 절대경로, `..`, Windows drive
prefix는 거부합니다.

## CLI 실행

### 받기 서버

```powershell
python -m server.server_main --host 0.0.0.0 --port 5001 --save-dir received
```

같은 PC에서 테스트할 때는 다음처럼 로컬호스트만 열어도 됩니다.

```powershell
python -m server.server_main --host 127.0.0.1 --port 5001 --save-dir received
```

### 단일 파일 보내기

```powershell
python -m client.client_main --host 127.0.0.1 --port 5001 --file testdata\sample.bin
```

### 여러 파일 보내기

```powershell
python -m client.client_main --host 127.0.0.1 --port 5001 --files testdata\a.txt testdata\b.txt
```

또는 `--file` 옵션을 반복할 수 있습니다.

```powershell
python -m client.client_main --host 127.0.0.1 --port 5001 --file testdata\a.txt --file testdata\b.txt
```

### 폴더 보내기

```powershell
python -m client.client_main --host 127.0.0.1 --port 5001 --folder testdata\folder_sample
```

서버에는 다음처럼 폴더 이름과 내부 구조가 함께 복원됩니다.

```text
received/
  folder_sample/
    root.txt
    docs/
      readme.txt
```

## GUI 실행

```powershell
python -m gui.connectbox_gui
```

권장 시연 순서:

1. 받는 PC에서 GUI 실행
2. `받기 모드`에서 Host `0.0.0.0`, Port `5001`, 저장 폴더 선택
3. `받기 서버 시작`
4. 보내는 PC에서 GUI 실행
5. `보내기 모드`에서 받는 PC의 IPv4 주소와 포트 입력
6. 파일 여러 개 또는 폴더 선택
7. `전송 시작`
8. 진행률, 상태 로그, 저장 폴더 구조 확인

## 자동 테스트

```powershell
python -m py_compile common\protocol.py server\server_main.py client\client_main.py gui\connectbox_gui.py scripts\smoke_test_local.py scripts\smoke_test_multi_files.py scripts\smoke_test_folder.py scripts\build_exe.py
python scripts\smoke_test_local.py --port 5011 --size-kb 10 --startup-wait 0.5
python scripts\smoke_test_multi_files.py --port 5012 --startup-wait 0.5
python scripts\smoke_test_folder.py --port 5013 --startup-wait 0.5
```

테스트가 성공하면 `PASS`를 출력합니다. 실패 시 `logs/` 아래의 서버/클라이언트
로그를 확인합니다.

## Windows 실행파일 패키징

PyInstaller는 개발 의존성으로 고정하지 않았습니다. exe가 필요할 때 패키징 PC에서만
설치합니다.

```powershell
python -m pip install pyinstaller
python scripts\build_exe.py --target all
```

결과물은 `dist/` 폴더에 생성됩니다.

개별 빌드:

```powershell
python scripts\build_exe.py --target gui
python scripts\build_exe.py --target client
python scripts\build_exe.py --target server
```

## LAN 시연 주의사항

- 받는 PC와 보내는 PC가 같은 Wi-Fi 또는 같은 유선 LAN에 있어야 합니다.
- 받는 PC에서 `ipconfig`로 IPv4 주소를 확인합니다.
- 다른 PC에서 접속하려면 서버 Host는 `0.0.0.0`을 사용합니다.
- Windows 방화벽 경고가 뜨면 현재 private network에서 Python 또는 exe 접근을 허용합니다.
- 포트를 바꾸면 서버와 클라이언트 모두 같은 포트를 사용해야 합니다.
