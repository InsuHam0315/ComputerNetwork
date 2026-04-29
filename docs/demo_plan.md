# 발표 시연 순서

## 1. 프로젝트 개요

같은 LAN의 두 Windows PC 사이에서 TCP 소켓으로 단일 파일을 직접 전송하는
CLI 프로그램입니다.

## 2. MVP 범위 설명

- TCP 기반 단일 파일 전송
- JSON 메타데이터 교환
- 청크 기반 파일 본문 전송
- 진행률과 완료 응답 출력
- Python 표준 라이브러리만 사용

## 3. 프로토콜 설명

```text
client -> server: FILE_SEND metadata
server -> client: READY
client -> server: file body chunks
server -> client: COMPLETE or ERROR
```

메타데이터 앞에는 4-byte 길이 값이 붙고, 이후 UTF-8 JSON이 전송됩니다.

## 4. 로컬 시연

```powershell
python -m server.server_main --host 127.0.0.1 --port 5001 --output-dir received
python scripts\create_dummy_file.py testdata\sample.bin --size 1048576
python -m client.client_main 127.0.0.1 testdata\sample.bin --port 5001
dir received
```

## 5. LAN 시연

서버 PC:

```powershell
ipconfig
python -m server.server_main --host 0.0.0.0 --port 5001 --output-dir received
```

클라이언트 PC:

```powershell
python scripts\create_dummy_file.py testdata\sample.bin --size 1048576
python -m client.client_main <SERVER_IPV4> testdata\sample.bin --port 5001
```

## 6. 결과 설명

- TCP 연결이 수립된 뒤 애플리케이션 계층 프로토콜이 동작합니다.
- 먼저 파일명과 파일 크기를 담은 메타데이터를 보냅니다.
- 서버가 받을 준비가 되면 `READY`를 응답합니다.
- 클라이언트는 파일 본문을 청크 단위로 전송합니다.
- 서버는 지정된 파일 크기만큼 수신하면 `COMPLETE`를 응답합니다.

## 7. 확장 계획

- 여러 파일 또는 폴더 전송
- 체크섬 검증
- 이어받기
- GUI
- 다중 클라이언트 처리
