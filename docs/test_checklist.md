# Test Checklist

This checklist separates the local smoke test from the real LAN test. The smoke
test only proves that the server and client can talk through `127.0.0.1` on one
PC. The final LAN check must still be performed on two Windows PCs connected to
the same network.

## Local Automated Smoke Test

1. Open PowerShell at the project root.
2. Compile the automation scripts.

```powershell
python -m py_compile scripts\create_dummy_file.py scripts\smoke_test_local.py
```

3. Create a small dummy file manually if needed.

```powershell
python scripts\create_dummy_file.py --output sample.bin --size-kb 10
```

4. Run the local smoke test.

```powershell
python scripts\smoke_test_local.py
```

5. Optional: run with an explicit port and file size.

```powershell
python scripts\smoke_test_local.py --port 5001 --size-kb 100
```

6. Confirm that the script prints `PASS`.
7. If it prints `FAIL`, open the log directory shown by the script and inspect
   `server_stdout.log`, `server_stderr.log`, `client_stdout.log`, and
   `client_stderr.log`.

## Same-LAN Two-PC Test

1. Connect both Windows PCs to the same Wi-Fi network or the same wired LAN.
2. On the server PC, open PowerShell at the project root.
3. Check the server PC IPv4 address.

```powershell
ipconfig
```

4. In the active network adapter section, find `IPv4 Address`. Use that address
   as `<SERVER_IPV4>` on the client PC.
5. Start the server on the server PC.

```powershell
python -m server.server_main --host 0.0.0.0 --port 5001 --save-dir received
```

6. On the client PC, create a test file.

```powershell
python scripts\create_dummy_file.py --output testdata\sample.bin --size-kb 100
```

7. On the client PC, send the file to the server PC.

```powershell
python -m client.client_main --host <SERVER_IPV4> --port 5001 --file testdata\sample.bin
```

8. On the server PC, check that the file appears in the `received` folder.
9. Compare the original file size and received file size.

## Windows Firewall Checks

- If Windows shows a Python firewall prompt on the server PC, allow access for
  the current private network.
- Confirm that the server PC network profile is private when possible.
- Confirm that TCP port `5001` is not blocked by Windows Defender Firewall or
  third-party security software.
- If changing the port, use the same port in both the server and client commands.

## Connection Failure Checklist

- Confirm the server command is already running before the client command.
- Confirm the server command uses `--host 0.0.0.0` for the LAN test.
- Confirm the client uses the server PC IPv4 address, not the client PC address.
- Confirm both PCs are on the same LAN and can reach each other.
- Confirm the server and client use the same TCP port.
- Check whether another process is already using the selected port.
- Review the server and client console output for connection or protocol errors.

## File Receive Failure Checklist

- Confirm the client file path exists and points to a file, not a folder.
- Confirm the server has permission to create files in the save directory.
- Check whether the received file was saved with a suffix such as `_1` because a
  file with the same name already existed.
- Compare source and received file sizes.
- Review server output for errors after the client connects.
- Review client output for errors after sending the file body.

## Demo Readiness Checklist

- Run `python -m py_compile scripts\create_dummy_file.py scripts\smoke_test_local.py`.
- Run `python scripts\smoke_test_local.py --size-kb 10` and confirm whether it
  prints `PASS` or a clear `FAIL` reason.
- Prepare two Windows PCs on the same LAN.
- Confirm the server PC IPv4 address with `ipconfig`.
- Confirm Windows Firewall allows Python on the server PC.
- Prepare a small test file first, then a larger file if time allows.
- Clear or note the `received` folder contents before the demo.
- Keep PowerShell windows open for both server and client output.
