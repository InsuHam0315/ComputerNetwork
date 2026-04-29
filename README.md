# TCP File Transfer MVP

같은 LAN에 있는 두 Windows PC 사이에서 TCP 소켓으로 단일 파일을 직접
전송하는 Python 표준 라이브러리 기반 CLI 프로젝트입니다.

중간발표 기준 목표는 GUI나 복잡한 전송 기능보다, TCP 연결 수립, 파일 메타데이터
교환, 청크 기반 파일 본문 전송, 완료 응답까지의 네트워크 흐름을 명확히 시연하는
것입니다.

## 중간발표용 MVP 범위

- Windows CLI에서 서버와 클라이언트를 각각 실행
- 같은 PC에서 `127.0.0.1`로 로컬 테스트
- 같은 LAN의 두 Windows PC에서 서버 PC IP로 LAN 테스트
- TCP 소켓 기반 단일 연결
- 단일 파일 1개 전송
- 파일명과 파일 크기를 JSON 메타데이터로 먼저 전송
- 파일 본문은 고정 크기 청크 단위로 전송
- 전송 진행률 출력
- 성공/실패 응답 출력
- Python 표준 라이브러리만 사용

## 제외한 기능

중간발표 MVP에서는 다음 기능을 제외합니다.

- 폴더 전송
- 여러 파일 동시 전송
- GUI
- 계정, 인증, 암호화
- 파일 이어받기
- 압축
- 멀티스레드 서버
- 여러 클라이언트 동시 접속
- 인터넷 경유 전송

## 최종발표 확장 예정 기능

- 여러 파일 또는 폴더 전송
- 전송 전 파일 덮어쓰기 확인
- 전송 결과 로그 저장
- 더 자세한 오류 메시지
- 이어받기 또는 체크섬 검증
- GUI 또는 간단한 설정 파일
- 다중 클라이언트 처리

## 프로젝트 구조

```text
client/
  client_main.py
server/
  server_main.py
common/
  protocol.py
  progress.py
docs/
  demo_plan.md
  testing.md
scripts/
  create_dummy_file.py
README.md
.gitignore
```

## 요청/응답 데이터 흐름

전송 흐름은 다음 순서를 따릅니다.

```text
1. client -> server: FILE_SEND 메타데이터
2. server -> client: READY 응답
3. client -> server: 파일 본문 bytes
4. server -> client: COMPLETE 또는 ERROR 응답
```

메타데이터는 길이 prefix가 붙은 JSON입니다.

```text
4-byte metadata length
JSON metadata
file body
```

예시:

```json
{"type":"FILE_SEND","filename":"sample.bin","filesize":1048576}
```

서버 응답도 같은 방식의 length-prefixed JSON을 사용합니다.

- `READY`: 파일 본문을 받을 준비 완료
- `COMPLETE`: 파일 수신 완료
- `ERROR`: 전송 실패

## TCP를 사용하는 이유

TCP는 연결 지향 프로토콜입니다. 파일 전송에서는 데이터가 빠지거나 순서가 바뀌면
파일이 깨질 수 있기 때문에, 순서 보장과 신뢰성 있는 전송이 중요합니다.

TCP는 다음 특징 때문에 이 프로젝트에 적합합니다.

- 송신한 byte stream의 순서 보장
- 손실된 패킷 재전송
- 흐름 제어와 혼잡 제어
- `sendall()`과 `recv()` 기반의 단순한 파일 스트림 구현 가능

UDP는 직접 재전송, 순서 재조립, 손실 처리 로직을 추가해야 하므로 중간발표용
MVP 범위에서는 TCP가 더 적합합니다.

## 청크 기반 전송 설명

파일 전체를 한 번에 메모리에 올리지 않고 일정 크기의 청크로 나누어 전송합니다.
현재 공통 진행률 모듈의 기본 청크 크기는 `64 * 1024` bytes, 즉 64 KB입니다.

청크 기반 전송을 사용하면 다음 장점이 있습니다.

- 큰 파일도 메모리를 과도하게 사용하지 않음
- 전송 중 진행률 계산 가능
- `recv()`가 요청한 크기보다 적은 bytes를 반환하는 TCP 특성을 처리하기 쉬움
- 파일 크기만큼 정확히 수신했는지 검증 가능

## 테스트용 더미 파일 생성

테스트용 파일은 직접 준비해도 되고, 보조 스크립트로 생성해도 됩니다.

```powershell
python scripts\create_dummy_file.py testdata\sample.bin --size 1048576
```

위 명령은 `testdata\sample.bin`에 1 MB 파일을 생성합니다.

## 서버 실행 방법

서버 PC에서 다음 명령을 실행합니다.

```powershell
python -m server.server_main --host 0.0.0.0 --port 5001 --output-dir received
```

옵션 의미:

- `--host 0.0.0.0`: 모든 네트워크 인터페이스에서 접속 허용
- `--port 5001`: TCP 5001번 포트 사용
- `--output-dir received`: 받은 파일을 `received` 폴더에 저장

로컬 PC 안에서만 테스트할 때는 다음처럼 실행해도 됩니다.

```powershell
python -m server.server_main --host 127.0.0.1 --port 5001 --output-dir received
```

## 클라이언트 실행 방법

클라이언트 PC에서 다음 명령을 실행합니다.

```powershell
python -m client.client_main <SERVER_IP> <FILE_PATH> --port 5001
```

예시:

```powershell
python -m client.client_main 127.0.0.1 testdata\sample.bin --port 5001
```

같은 LAN의 다른 PC로 보낼 때는 `127.0.0.1` 대신 서버 PC의 IPv4 주소를 넣습니다.

```powershell
python -m client.client_main 192.168.0.25 testdata\sample.bin --port 5001
```

## 127.0.0.1 로컬 테스트 방법

한 PC에서 PowerShell 창을 2개 엽니다.

1. 첫 번째 PowerShell에서 서버 실행

```powershell
python -m server.server_main --host 127.0.0.1 --port 5001 --output-dir received
```

2. 두 번째 PowerShell에서 테스트 파일 생성

```powershell
python scripts\create_dummy_file.py testdata\sample.bin --size 1048576
```

3. 두 번째 PowerShell에서 클라이언트 실행

```powershell
python -m client.client_main 127.0.0.1 testdata\sample.bin --port 5001
```

4. 확인할 내용

- 서버가 `READY` 이후 파일 본문을 수신하는지 확인
- 클라이언트가 진행률을 출력하는지 확인
- 서버가 `COMPLETE` 응답을 보내는지 확인
- `received` 폴더에 받은 파일이 생성되는지 확인
- 원본 파일 크기와 수신 파일 크기가 같은지 확인

주의: 현재 `server_main.py`와 `client_main.py`가 골격 상태라면 실제 소켓 전송 대신
준비 메시지와 TODO 메시지만 출력됩니다. 서버/클라이언트 구현이 완료된 뒤 위 절차로
실제 전송을 검증합니다.

## 같은 LAN 테스트 방법

준비 조건:

- 두 Windows PC가 같은 Wi-Fi 또는 같은 공유기 LAN에 연결되어 있어야 함
- 서버 PC와 클라이언트 PC에 Python이 설치되어 있어야 함
- 두 PC 모두 같은 프로젝트 코드를 가지고 있어야 함
- 서버 PC의 방화벽에서 TCP 5001번 포트 접속이 허용되어야 함

1. 서버 PC에서 IPv4 주소 확인

```powershell
ipconfig
```

`무선 LAN 어댑터 Wi-Fi` 또는 `이더넷 어댑터 이더넷` 항목에서 `IPv4 주소`를
확인합니다. 예: `192.168.0.25`

2. 서버 PC에서 서버 실행

```powershell
python -m server.server_main --host 0.0.0.0 --port 5001 --output-dir received
```

3. 클라이언트 PC에서 테스트 파일 생성

```powershell
python scripts\create_dummy_file.py testdata\sample.bin --size 1048576
```

4. 클라이언트 PC에서 서버 IP로 접속

```powershell
python -m client.client_main 192.168.0.25 testdata\sample.bin --port 5001
```

5. 확인할 내용

- 클라이언트가 서버 IP와 TCP 5001번 포트로 연결되는지 확인
- 서버 화면에 클라이언트 접속과 파일 수신 로그가 표시되는지 확인
- 수신 폴더에 파일이 저장되는지 확인
- 전송 완료 응답이 출력되는지 확인

## Windows 서버 PC IP 확인 방법

PowerShell 또는 명령 프롬프트에서 다음 명령을 실행합니다.

```powershell
ipconfig
```

확인할 항목:

- Wi-Fi 사용 시: `무선 LAN 어댑터 Wi-Fi`
- 유선 LAN 사용 시: `이더넷 어댑터 이더넷`
- 사용할 값: `IPv4 주소`

주의할 점:

- `127.0.0.1`은 자기 자신을 뜻하므로 다른 PC에서 접속할 때 사용할 수 없습니다.
- `169.254.x.x` 형태의 주소는 정상적인 공유기 LAN 주소가 아닐 가능성이 높습니다.
- 보통 가정/강의실 공유기에서는 `192.168.x.x` 또는 `10.x.x.x` 형태가 많이 사용됩니다.

## Windows 방화벽 주의사항

LAN 테스트에서 서버가 실행 중인데 클라이언트 연결이 실패하면 Windows 방화벽이
차단하고 있을 수 있습니다.

확인 방법:

- 서버 실행 시 Windows 보안 경고 창이 뜨면 개인 네트워크 허용을 선택
- Windows 보안 > 방화벽 및 네트워크 보호 > 앱 허용에서 Python 허용 여부 확인
- 필요하면 인바운드 규칙에서 TCP 5001번 포트 허용

공용 Wi-Fi나 학교 네트워크에서는 같은 Wi-Fi에 있어도 기기 간 통신이 차단될 수
있습니다. 이 경우 휴대폰 핫스팟이나 개인 공유기처럼 기기 간 통신이 허용되는
네트워크에서 테스트합니다.

## 발표 시연 시나리오

1. 프로젝트 목표 설명

```text
같은 LAN의 두 Windows PC 사이에서 TCP 소켓으로 단일 파일을 직접 전송한다.
```

2. 프로토콜 흐름 설명

```text
FILE_SEND metadata -> READY -> file body chunks -> COMPLETE
```

3. 로컬 테스트 시연

```powershell
python -m server.server_main --host 127.0.0.1 --port 5001 --output-dir received
python scripts\create_dummy_file.py testdata\sample.bin --size 1048576
python -m client.client_main 127.0.0.1 testdata\sample.bin --port 5001
```

4. LAN 테스트 시연

```powershell
ipconfig
python -m server.server_main --host 0.0.0.0 --port 5001 --output-dir received
python -m client.client_main <SERVER_IPV4> testdata\sample.bin --port 5001
```

5. 결과 확인

```powershell
dir received
```

6. 네트워크 과목 관점 설명

- TCP 연결을 통해 신뢰성 있는 byte stream을 사용함
- 애플리케이션 계층에서 메타데이터 길이와 JSON 구조를 정의함
- 파일 본문은 청크 단위로 나누어 송수신함
- 서버와 클라이언트의 요청/응답 순서를 직접 설계함

## 트러블슈팅

### 서버가 안 켜지는 경우

- 포트가 이미 사용 중일 수 있습니다. 다른 PowerShell에서 실행 중인 서버를 종료하거나
  `--port 5002`처럼 다른 포트를 사용합니다.
- Python 명령이 인식되지 않으면 Python 설치와 PATH 설정을 확인합니다.
- 프로젝트 루트가 아닌 폴더에서 실행하면 모듈 실행이 실패할 수 있습니다.
  `README.md`가 있는 프로젝트 루트에서 실행합니다.

### 연결이 안 되는 경우

- 서버가 먼저 실행되어 있어야 합니다.
- 클라이언트의 IP 주소가 서버 PC의 IPv4 주소와 일치하는지 확인합니다.
- 서버와 클라이언트의 포트 번호가 같은지 확인합니다.
- LAN 테스트에서는 서버를 `--host 0.0.0.0`으로 실행합니다.
- 두 PC가 같은 네트워크에 연결되어 있는지 확인합니다.

### 방화벽 문제

- 서버 PC에서 Python의 네트워크 접근을 허용합니다.
- Windows 방화벽 인바운드 규칙에서 TCP 5001번 포트를 허용합니다.
- 공용 네트워크로 잡혀 있으면 개인 네트워크로 바꾸거나 허용 규칙을 추가합니다.

### IP 주소 확인 방법

- 서버 PC에서 `ipconfig` 실행
- `IPv4 주소` 확인
- 클라이언트 명령의 `<SERVER_IP>`에 해당 값을 입력
- `127.0.0.1`은 로컬 테스트에서만 사용

### 받은 파일이 안 보이는 경우

- 서버 실행 시 지정한 `--output-dir` 값을 확인합니다.
- 기본 예시는 `received` 폴더를 사용합니다.
- 같은 이름의 파일 처리 정책은 서버 구현 단계의 동작을 따릅니다.

## 검증 명령

문서와 보조 스크립트 작업 후 다음 명령으로 확인합니다.

```powershell
dir
python -m py_compile scripts\create_dummy_file.py
git diff -- README.md docs scripts
```
