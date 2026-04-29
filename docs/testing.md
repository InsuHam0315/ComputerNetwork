# 테스트 절차

이 문서는 중간발표 MVP의 로컬 테스트와 같은 LAN 테스트 절차를 분리해 정리합니다.

## 로컬 테스트

목적: 서버와 클라이언트를 같은 PC에서 실행해 프로토콜 흐름을 빠르게 확인합니다.

1. PowerShell 창 2개를 엽니다.
2. 첫 번째 창에서 서버를 실행합니다.

```powershell
python -m server.server_main --host 127.0.0.1 --port 5001 --output-dir received
```

3. 두 번째 창에서 테스트 파일을 생성합니다.

```powershell
python scripts\create_dummy_file.py testdata\sample.bin --size 1048576
```

4. 두 번째 창에서 클라이언트를 실행합니다.

```powershell
python -m client.client_main 127.0.0.1 testdata\sample.bin --port 5001
```

5. `received` 폴더에 파일이 생겼는지 확인합니다.

```powershell
dir received
```

현재 서버/클라이언트가 골격 상태라면 실제 전송 대신 준비 메시지와 TODO 메시지만
출력됩니다.

## 같은 LAN 테스트

목적: 두 Windows PC 사이에서 실제 네트워크를 거치는 TCP 연결을 확인합니다.

1. 서버 PC와 클라이언트 PC를 같은 Wi-Fi 또는 같은 공유기 LAN에 연결합니다.
2. 서버 PC에서 IPv4 주소를 확인합니다.

```powershell
ipconfig
```

3. 서버 PC에서 서버를 실행합니다.

```powershell
python -m server.server_main --host 0.0.0.0 --port 5001 --output-dir received
```

4. 클라이언트 PC에서 테스트 파일을 생성합니다.

```powershell
python scripts\create_dummy_file.py testdata\sample.bin --size 1048576
```

5. 클라이언트 PC에서 서버 IPv4 주소로 접속합니다.

```powershell
python -m client.client_main <SERVER_IPV4> testdata\sample.bin --port 5001
```

6. 서버 PC의 `received` 폴더와 양쪽 콘솔 로그를 확인합니다.

## 확인 포인트

- 서버가 먼저 실행되어 있는가
- 서버 IP와 클라이언트 입력 IP가 같은가
- 서버 포트와 클라이언트 포트가 같은가
- Windows 방화벽에서 Python 또는 TCP 5001번 포트를 허용했는가
- 같은 LAN에서 기기 간 통신이 허용되는 네트워크인가
