# ConnectBox 테스트 가이드

이 문서는 최종발표 버전의 로컬 자동 테스트와 실제 LAN 테스트 절차를 정리합니다.

## 1. 컴파일 확인

```powershell
python -m py_compile common\protocol.py server\server_main.py client\client_main.py gui\connectbox_gui.py scripts\smoke_test_local.py scripts\smoke_test_multi_files.py scripts\smoke_test_folder.py scripts\build_exe.py
```

## 2. 로컬 자동 테스트

각 테스트는 서버 프로세스를 로컬에서 띄우고 클라이언트를 실행한 뒤 결과 파일을
검증합니다.

```powershell
python scripts\smoke_test_local.py --port 5011 --size-kb 10 --startup-wait 0.5
python scripts\smoke_test_multi_files.py --port 5012 --startup-wait 0.5
python scripts\smoke_test_folder.py --port 5013 --startup-wait 0.5
```

검증 항목:

- 단일 파일 전송 PASS
- 다중 파일 3개 전송 PASS
- 폴더 전송 4개 파일 PASS
- 중첩 폴더 구조 복원
- 빈 파일 전송 처리

실패하면 출력된 `logs/...` 경로에서 다음 파일을 확인합니다.

- `server_stdout.log`
- `server_stderr.log`
- `client_stdout.log`
- `client_stderr.log`

## 3. CLI 수동 테스트

PowerShell 창 두 개를 엽니다.

서버:

```powershell
python -m server.server_main --host 127.0.0.1 --port 5001 --save-dir received
```

클라이언트:

```powershell
python scripts\create_dummy_file.py --output testdata\manual.bin --size-kb 100
python -m client.client_main --host 127.0.0.1 --port 5001 --file testdata\manual.bin
```

여러 파일:

```powershell
python -m client.client_main --host 127.0.0.1 --port 5001 --files testdata\a.txt testdata\b.txt
```

폴더:

```powershell
python -m client.client_main --host 127.0.0.1 --port 5001 --folder testdata\folder_sample
```

## 4. GUI 수동 테스트

```powershell
python -m gui.connectbox_gui
```

확인 항목:

- 받기 모드에서 서버 시작 가능
- 보내기 모드에서 파일 여러 개 선택 가능
- 보내기 모드에서 폴더 선택 가능
- 현재 파일 진행률 표시
- 전체 진행률 표시
- 상태 로그 표시
- 저장 폴더에 파일/폴더 구조 생성

## 5. 같은 LAN 두 PC 테스트

서버 PC:

```powershell
ipconfig
python -m server.server_main --host 0.0.0.0 --port 5001 --save-dir received
```

클라이언트 PC:

```powershell
python -m client.client_main --host <SERVER_IPV4> --port 5001 --folder testdata\folder_sample
```

주의:

- `<SERVER_IPV4>`는 서버 PC의 IPv4 주소입니다.
- `127.0.0.1`은 자기 자신을 의미하므로 다른 PC에서 접속할 때 사용할 수 없습니다.
- Windows 방화벽이 Python 또는 exe의 TCP 수신을 막을 수 있습니다.
