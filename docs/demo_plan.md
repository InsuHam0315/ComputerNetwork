# ConnectBox 최종발표 시연 계획

## 1. 프로젝트 한 줄 소개

ConnectBox는 같은 LAN에 있는 Windows PC 사이에서 중앙 서버나 클라우드 없이
TCP socket으로 파일을 직접 전송하는 Python 기반 앱입니다.

## 2. 중간발표 대비 확장점

- CLI 단일 파일 전송 유지
- 다중 파일 전송 추가
- 폴더 전송 추가
- 폴더 구조 복원 추가
- 전송 세션 프로토콜 v2 추가
- 현재 파일/전체 진행률 표시
- Tkinter GUI 추가
- 자동 테스트 3종으로 확장
- Windows exe 패키징 준비

## 3. 아키텍처 설명

```text
GUI / CLI
  |
  v
client.client_main.send_paths()
  |
  v
common.protocol metadata helpers
  |
  v
TCP socket
  |
  v
server.server_main.run_server()
  |
  v
received/ 폴더에 저장
```

GUI는 전송 로직을 다시 구현하지 않고 CLI와 같은 core 함수를 호출합니다.

## 4. 프로토콜 설명

### v1

단일 파일 호환용입니다.

```text
FILE_SEND -> READY -> bytes -> COMPLETE
```

### v2

다중 파일/폴더용 세션 프로토콜입니다.

```text
TRANSFER_START
FILE_ITEM -> bytes -> FILE_DONE
FILE_ITEM -> bytes -> FILE_DONE
TRANSFER_END
```

폴더 전송은 `relative_path`를 사용해 서버에서 원래 구조를 복원합니다.

## 5. 로컬 시연 순서

1. GUI 실행

```powershell
python -m gui.connectbox_gui
```

2. 받기 모드에서 Host `127.0.0.1`, Port `5001`, 저장 폴더 `received` 선택
3. 받기 서버 시작
4. 보내기 모드에서 서버 IP `127.0.0.1`, Port `5001` 입력
5. 파일 여러 개 선택 후 전송
6. 진행률과 로그 확인
7. 다시 받기 서버 시작
8. 폴더 선택 후 전송
9. `received/선택한폴더명/...` 구조 복원 확인

## 6. 자동 테스트 시연

```powershell
python scripts\smoke_test_local.py --port 5011 --size-kb 10 --startup-wait 0.5
python scripts\smoke_test_multi_files.py --port 5012 --startup-wait 0.5
python scripts\smoke_test_folder.py --port 5013 --startup-wait 0.5
```

세 명령 모두 `PASS`를 출력하는 것을 보여줍니다.

## 7. LAN 시연 순서

서버 PC:

```powershell
ipconfig
python -m gui.connectbox_gui
```

- 받기 모드 Host: `0.0.0.0`
- Port: `5001`
- 받기 서버 시작

클라이언트 PC:

```powershell
python -m gui.connectbox_gui
```

- 보내기 모드 서버 IP: 서버 PC IPv4
- Port: `5001`
- 파일 또는 폴더 선택
- 전송 시작

## 8. 발표 중 강조할 점

- TCP는 byte stream이므로 메타데이터 길이 prefix를 직접 설계했다.
- 파일 본문은 chunk 단위로 보내므로 큰 파일도 전체를 메모리에 올리지 않는다.
- v1을 유지해 기존 MVP 테스트를 깨지 않았다.
- v2는 세션 단위라 파일 여러 개와 폴더를 같은 흐름으로 처리한다.
- 서버는 `relative_path`를 검증해 경로 탈출을 막고 저장 폴더 안에만 쓴다.
- GUI는 표준 Tkinter만 사용해 외부 GUI 의존성을 늘리지 않았다.
