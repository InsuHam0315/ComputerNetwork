"""Generate the ConnectBox midterm presentation and speaker script.

The environment does not assume python-pptx is installed, so this script writes
the minimal PowerPoint Open XML package directly.
"""

from __future__ import annotations

import html
import zipfile
from pathlib import Path


OUT_DIR = Path("outputs")
PPTX_PATH = OUT_DIR / "ConnectBox_중간발표.pptx"
SCRIPT_PATH = OUT_DIR / "ConnectBox_중간발표_발표대본.md"

SLIDE_W = 12_192_000
SLIDE_H = 6_858_000

COLORS = {
    "bg": "F7F8FA",
    "white": "FFFFFF",
    "text": "1F2933",
    "muted": "5B677A",
    "line": "D8DEE8",
    "teal": "0E7C7B",
    "teal_dark": "075E5D",
    "orange": "F2A541",
    "green": "2F9E44",
    "red": "C92A2A",
    "navy": "243B53",
}


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def emu(cm: float) -> int:
    return int(cm * 360_000)


def text_run(text: str, size: int, color: str, bold: bool = False) -> str:
    b = ' b="1"' if bold else ""
    return (
        f'<a:r><a:rPr lang="ko-KR" sz="{size}"{b} dirty="0">'
        f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
        '<a:latin typeface="Malgun Gothic"/><a:ea typeface="Malgun Gothic"/>'
        "</a:rPr>"
        f"<a:t>{esc(text)}</a:t></a:r>"
    )


def paragraph(
    text: str,
    size: int = 2200,
    color: str = COLORS["text"],
    bold: bool = False,
    align: str = "l",
) -> str:
    return (
        f'<a:p><a:pPr algn="{align}"><a:buNone/></a:pPr>'
        f"{text_run(text, size, color, bold)}</a:p>"
    )


def tx_body(
    lines: list[str],
    size: int = 2200,
    color: str = COLORS["text"],
    bold_first: bool = False,
    align: str = "l",
    anchor: str = "t",
) -> str:
    body = [f'<a:bodyPr wrap="square" anchor="{anchor}"><a:spAutoFit/></a:bodyPr><a:lstStyle/>']
    for idx, line in enumerate(lines):
        body.append(paragraph(line, size, color, bold_first and idx == 0, align))
    return "<p:txBody>" + "".join(body) + "</p:txBody>"


def shape(
    sid: int,
    name: str,
    x: int,
    y: int,
    w: int,
    h: int,
    fill: str | None = None,
    line: str | None = None,
    text: list[str] | None = None,
    text_size: int = 2200,
    text_color: str = COLORS["text"],
    bold_first: bool = False,
    align: str = "l",
    anchor: str = "t",
    preset: str = "rect",
) -> str:
    fill_xml = '<a:noFill/>' if fill is None else f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>'
    line_xml = '<a:ln><a:noFill/></a:ln>' if line is None else f'<a:ln w="12700"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>'
    text_xml = ""
    tx_box = ' txBox="1"'
    if text is not None:
        text_xml = tx_body(text, text_size, text_color, bold_first, align, anchor)
    return f"""
<p:sp>
  <p:nvSpPr><p:cNvPr id="{sid}" name="{esc(name)}"/><p:cNvSpPr{tx_box}/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>
    <a:prstGeom prst="{preset}"><a:avLst/></a:prstGeom>
    {fill_xml}{line_xml}
  </p:spPr>
  {text_xml}
</p:sp>
"""


def title(sid: int, text: str, subtitle: str | None = None) -> str:
    parts = [
        shape(sid, "Title", emu(0.75), emu(0.45), emu(11.0), emu(0.62), None, None, [text], 3000, COLORS["text"], True),
        shape(sid + 1, "Title Accent", emu(0.75), emu(1.17), emu(2.0), emu(0.06), COLORS["teal"], None),
    ]
    if subtitle:
        parts.append(shape(sid + 2, "Subtitle", emu(0.75), emu(1.28), emu(10.8), emu(0.35), None, None, [subtitle], 1350, COLORS["muted"]))
    return "".join(parts)


def footer(slide_no: int) -> str:
    return (
        shape(940, "Footer Line", emu(0.75), emu(18.42), emu(32.0), emu(0.02), COLORS["line"], None)
        + shape(941, "Footer Text", emu(0.75), emu(18.52), emu(8.0), emu(0.28), None, None, ["ConnectBox 중간발표"], 1050, COLORS["muted"])
        + shape(942, "Slide Number", emu(31.0), emu(18.52), emu(1.0), emu(0.28), None, None, [str(slide_no)], 1050, COLORS["muted"], False, "r")
    )


def card(sid: int, x: float, y: float, w: float, h: float, heading: str, lines: list[str], accent: str = "teal") -> str:
    text = [heading] + lines
    return (
        shape(sid, f"{heading} Card", emu(x), emu(y), emu(w), emu(h), COLORS["white"], COLORS["line"])
        + shape(sid + 1, f"{heading} Accent", emu(x), emu(y), emu(0.10), emu(h), COLORS[accent], None)
        + shape(sid + 2, f"{heading} Text", emu(x + 0.25), emu(y + 0.20), emu(w - 0.45), emu(h - 0.35), None, None, text, 1500, COLORS["text"], True)
    )


def code_box(sid: int, x: float, y: float, w: float, h: float, lines: list[str]) -> str:
    return shape(sid, "Code Box", emu(x), emu(y), emu(w), emu(h), "1F2933", "1F2933", lines, 1250, COLORS["white"], False, "l")


def slide_xml(slide_no: int, shapes_xml: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:bg><p:bgPr><a:solidFill><a:srgbClr val="{COLORS['bg']}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      {shapes_xml}
      {footer(slide_no)}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>
"""


def rels_for_slide() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>
"""


def build_slides() -> list[str]:
    slides: list[str] = []

    slides.append(slide_xml(1, "".join([
        shape(10, "Cover Band", 0, 0, SLIDE_W, emu(1.1), COLORS["teal_dark"], None),
        shape(11, "Cover Title", emu(0.95), emu(3.6), emu(10.4), emu(1.2), None, None, ["ConnectBox"], 5200, COLORS["text"], True),
        shape(12, "Cover Subtitle", emu(1.02), emu(5.0), emu(10.7), emu(0.9), None, None, ["LAN 기반 Windows-to-Windows 파일 전송 도구", "컴퓨터네트워크 중간발표"], 2100, COLORS["muted"]),
        shape(13, "Cover Meta", emu(1.02), emu(7.35), emu(10.7), emu(0.75), None, None, ["2201346 함인수 | 2026.04.30"], 1700, COLORS["text"]),
        shape(14, "Cover Diagram 1", emu(7.0), emu(2.2), emu(1.55), emu(0.8), COLORS["white"], COLORS["line"], ["송신 PC"], 1500, COLORS["text"], False, "c", "mid"),
        shape(15, "Cover Arrow", emu(8.55), emu(2.35), emu(1.5), emu(0.45), None, None, ["TCP"], 1600, COLORS["teal"], True, "c"),
        shape(16, "Cover Diagram 2", emu(10.05), emu(2.2), emu(1.55), emu(0.8), COLORS["white"], COLORS["line"], ["수신 PC"], 1500, COLORS["text"], False, "c", "mid"),
        shape(17, "Cover Arrow Shape", emu(8.55), emu(2.88), emu(1.5), emu(0.04), COLORS["orange"], None),
    ])))

    slides.append(slide_xml(2, title(10, "발표 흐름", "5분 내외 중간발표 구성") + "".join([
        card(20, 1.0, 2.0, 3.2, 1.25, "1. 문제와 목표", ["개발 배경", "문제 정의"], "teal"),
        card(30, 4.65, 2.0, 3.2, 1.25, "2. 설계", ["시스템 구조", "프로토콜 흐름"], "orange"),
        card(40, 8.3, 2.0, 3.2, 1.25, "3. 구현", ["현재 구현 기능", "실행 및 배포"], "green"),
        card(50, 3.0, 4.15, 3.2, 1.25, "4. 검증", ["로컬 전송 테스트", "데모 캡처 위치"], "teal"),
        card(60, 6.65, 4.15, 3.2, 1.25, "5. 남은 작업", ["확장 기능", "마무리 계획"], "orange"),
    ])))

    slides.append(slide_xml(3, title(10, "프로젝트 개요", "같은 LAN 안의 두 Windows PC 사이에서 단일 파일을 직접 전송") + "".join([
        card(20, 0.95, 1.85, 3.25, 2.0, "목표", ["클라우드나 USB 없이", "TCP 소켓으로 파일 전송", "수신 PC에 자동 저장"], "teal"),
        card(30, 4.5, 1.85, 3.25, 2.0, "형태", ["서버-클라이언트 CLI", "Python 표준 라이브러리", "Windows 실행 파일 제공"], "orange"),
        card(40, 8.05, 1.85, 3.25, 2.0, "중간발표 기준", ["단일 파일 전송 MVP", "로컬 전송 성공", "릴리스 패키지 구성"], "green"),
        shape(50, "Summary", emu(1.05), emu(4.55), emu(10.3), emu(0.82), "E8F6F6", "B7DFDF", ["핵심 메시지: 최종 기능 전체가 아니라, TCP 기반 파일 전송의 최소 동작 흐름을 완성하고 배포 가능한 형태로 정리했습니다."], 1550, COLORS["text"]),
    ])))

    slides.append(slide_xml(4, title(10, "개발 배경 및 문제 정의", "제안발표의 문제의식을 중간발표 구현 범위로 구체화") + "".join([
        card(20, 0.95, 1.85, 3.3, 2.65, "배경", ["새 PC 세팅 시 파일 이동 반복", "USB/외장 저장장치 사용 번거로움", "클라우드 업로드·다운로드 대기"], "teal"),
        card(30, 4.45, 1.85, 3.3, 2.65, "문제", ["같은 LAN에 있어도 직접 전송 수단 부족", "파일 전송 과정이 불필요하게 우회", "수업 개념을 실제 동작으로 확인할 필요"], "orange"),
        card(40, 7.95, 1.85, 3.3, 2.65, "해결 방향", ["수신 PC를 서버로 실행", "송신 PC에서 서버 IP로 접속", "TCP byte stream으로 파일 전송"], "green"),
    ])))

    slides.append(slide_xml(5, title(10, "중간발표 MVP 범위", "구현 완료와 향후 구현 예정 기능을 분리") + "".join([
        card(20, 0.95, 1.8, 5.0, 3.45, "구현 완료", ["단일 파일 1개 전송", "JSON 메타데이터 교환", "READY / COMPLETE / ERROR 응답", "청크 기반 송수신 및 진행률 출력", "Windows 실행 파일 패키징"], "green"),
        card(30, 6.25, 1.8, 5.0, 3.45, "향후 구현 예정", ["폴더 전송", "여러 파일 동시 전송", "GUI", "체크섬 검증 및 이어받기", "다중 클라이언트 처리"], "orange"),
        shape(40, "Boundary", emu(1.05), emu(5.65), emu(10.2), emu(0.55), "FFF4E6", "F2A541", ["중간발표에서는 GUI보다 네트워크 흐름과 파일 전송 프로토콜 동작을 우선 검증했습니다."], 1450, COLORS["text"]),
    ])))

    slides.append(slide_xml(6, title(10, "시스템 전체 구조", "수신 PC는 서버, 송신 PC는 클라이언트로 역할을 분리") + "".join([
        shape(20, "Client Box", emu(0.95), emu(2.1), emu(3.0), emu(2.2), COLORS["white"], COLORS["line"], ["송신 PC", "client.exe", "파일 선택", "서버 IP로 접속"], 1600, COLORS["text"], True, "c", "mid"),
        shape(30, "Network Box", emu(4.6), emu(2.25), emu(2.85), emu(1.9), "E8F6F6", COLORS["teal"], ["같은 LAN", "TCP 5001", "byte stream"], 1600, COLORS["text"], True, "c", "mid"),
        shape(40, "Server Box", emu(8.1), emu(2.1), emu(3.0), emu(2.2), COLORS["white"], COLORS["line"], ["수신 PC", "server.exe", "포트 대기", "received 폴더 저장"], 1600, COLORS["text"], True, "c", "mid"),
        shape(50, "Arrow1", emu(3.95), emu(2.95), emu(0.65), emu(0.35), None, None, ["→"], 2500, COLORS["orange"], True, "c"),
        shape(51, "Arrow2", emu(7.45), emu(2.95), emu(0.65), emu(0.35), None, None, ["→"], 2500, COLORS["orange"], True, "c"),
        shape(60, "Note", emu(1.25), emu(5.1), emu(9.7), emu(0.65), None, None, ["서버는 한 클라이언트 접속을 받아 파일을 저장하고, 클라이언트는 파일 본문을 지정 크기만큼 전송합니다."], 1450, COLORS["muted"], False, "c"),
    ])))

    slides.append(slide_xml(7, title(10, "프로토콜 및 실행 흐름", "애플리케이션 계층에서 메타데이터와 응답 형식을 직접 정의") + "".join([
        card(20, 0.8, 1.82, 2.55, 1.25, "1", ["FILE_SEND", "파일명·파일 크기"], "teal"),
        card(30, 3.55, 1.82, 2.1, 1.25, "2", ["READY", "수신 준비"], "orange"),
        card(40, 5.85, 1.82, 2.65, 1.25, "3", ["file body", "청크 단위 bytes"], "teal"),
        card(50, 8.7, 1.82, 2.55, 1.25, "4", ["COMPLETE", "수신 완료 응답"], "green"),
        code_box(60, 1.1, 4.0, 10.0, 1.25, [
            "4-byte metadata length  +  UTF-8 JSON metadata  +  file body bytes",
            '{"type":"FILE_SEND","filename":"sample.bin","filesize":10240}',
        ]),
        shape(70, "Protocol Note", emu(1.1), emu(5.55), emu(10.0), emu(0.55), None, None, ["TCP는 byte stream이므로, 메타데이터 길이를 먼저 보내 수신 측이 JSON 경계를 정확히 판단하도록 했습니다."], 1350, COLORS["muted"]),
    ])))

    slides.append(slide_xml(8, title(10, "주요 구현 기능", "실제 코드 기준으로 확인한 구현 항목") + "".join([
        card(20, 0.85, 1.8, 3.25, 1.55, "client", ["파일 경로 검증", "서버 연결", "메타데이터·본문 전송"], "teal"),
        card(30, 4.45, 1.8, 3.25, 1.55, "server", ["포트 listen", "파일 저장", "중복 파일명 처리"], "orange"),
        card(40, 8.05, 1.8, 3.25, 1.55, "common", ["length-prefixed JSON", "응답 검증", "진행률 포맷"], "green"),
        card(50, 0.85, 3.85, 3.25, 1.55, "scripts", ["더미 파일 생성", "로컬 smoke test", "로그 저장"], "teal"),
        card(60, 4.45, 3.85, 3.25, 1.55, "dist", ["server.exe", "client.exe", "ConnectBox_v1.0.zip"], "orange"),
        card(70, 8.05, 3.85, 3.25, 1.55, "docs", ["테스트 체크리스트", "데모 절차", "실행 방법"], "green"),
    ])))

    slides.append(slide_xml(9, title(10, "실행 및 배포 방식", "다운로드 후 바로 실행할 수 있는 Windows 배포 형태") + "".join([
        card(20, 0.95, 1.8, 4.8, 2.0, "배포 구성", ["server.exe: 파일 수신 PC에서 실행", "client.exe: 파일 송신 PC에서 실행", "실행방법.txt 포함"], "green"),
        card(30, 6.05, 1.8, 5.2, 2.0, "GitHub Release v1.0", ["ConnectBox_v1.0.zip 업로드", "실행 파일과 사용 방법 제공", "다운로드 주소를 함께 안내"], "teal"),
        code_box(40, 1.0, 4.45, 10.2, 1.25, [
            "server.exe --host 0.0.0.0 --port 5001 --save-dir received",
            "client.exe --host <SERVER_IP> --port 5001 --file <FILE_PATH>",
        ]),
        shape(50, "Release URL", emu(1.0), emu(5.95), emu(10.2), emu(0.35), None, None, ["Release URL: https://github.com/InsuHam0315/ComputerNetwork/releases/tag/v1.0"], 1050, COLORS["muted"]),
    ])))

    slides.append(slide_xml(10, title(10, "검증 결과 및 데모 자료", "현재 확인된 범위만 구현 완료로 표시") + "".join([
        shape(20, "Screenshot Placeholder", emu(0.95), emu(1.8), emu(6.25), emu(3.8), COLORS["white"], COLORS["line"], ["실행 캡처 이미지 삽입 위치", "서버/클라이언트 콘솔", "수신 폴더 결과 화면"], 1700, COLORS["muted"], True, "c", "mid"),
        card(30, 7.55, 1.85, 3.8, 1.15, "확인 완료", ["py_compile 통과", "로컬 smoke test PASS"], "green"),
        card(40, 7.55, 3.25, 3.8, 1.15, "테스트 범위", ["127.0.0.1 로컬 전송", "10KB 샘플 파일 수신 확인"], "teal"),
        card(50, 7.55, 4.65, 3.8, 1.15, "추가 확인", ["동일 LAN 두 PC 테스트", "발표 전 캡처 삽입"], "orange"),
    ])))

    slides.append(slide_xml(11, title(10, "구현 중 문제와 해결 과정", "MVP 완성 과정에서 확인한 주요 이슈") + "".join([
        card(20, 0.95, 1.75, 3.25, 2.55, "메시지 경계", ["TCP는 메시지 단위가 아님", "4-byte 길이 prefix 사용", "JSON 크기 제한 적용"], "teal"),
        card(30, 4.5, 1.75, 3.25, 2.55, "파일 크기 검증", ["filesize만큼 반복 수신", "recv() 부분 수신 처리", "중도 종료 시 오류 처리"], "orange"),
        card(40, 8.05, 1.75, 3.25, 2.55, "실행 환경", ["방화벽 허용 필요", "포트 사용 중이면 변경", "exe와 실행방법 동시 배포"], "green"),
        shape(50, "Issue Note", emu(1.05), emu(4.95), emu(10.2), emu(0.75), "EEF2F7", COLORS["line"], ["자동 테스트 중 기본 포트가 이미 사용 중일 수 있어, 검증 시 다른 포트로도 실행 가능하도록 절차를 정리했습니다."], 1400, COLORS["text"]),
    ])))

    slides.append(slide_xml(12, title(10, "남은 작업 및 기대 효과", "최종발표까지의 확장 방향") + "".join([
        card(20, 0.95, 1.8, 5.0, 2.85, "남은 작업", ["동일 LAN 두 PC 환경에서 반복 검증", "체크섬 기반 무결성 확인", "폴더/다중 파일 전송", "GUI 또는 설정 파일 추가"], "orange"),
        card(30, 6.25, 1.8, 5.0, 2.85, "기대 효과", ["LAN 내 직접 전송으로 사용 편의성 개선", "TCP 소켓 흐름을 실제 코드로 학습", "배포 가능한 네트워크 도구 형태 확보", "최종 확장 기능의 기반 마련"], "green"),
        shape(40, "Closing", emu(1.0), emu(5.25), emu(10.2), emu(0.8), "E8F6F6", "B7DFDF", ["마무리: 중간발표 기준으로 단일 파일 전송 MVP와 실행 파일 배포까지 완료했습니다."], 1650, COLORS["text"], True, "c", "mid"),
    ])))

    return slides


NOTES = [
    ("표지", "안녕하세요. 2201346 함인수입니다. 이번 중간발표에서는 LAN 기반 Windows-to-Windows 파일 전송 도구인 ConnectBox의 현재 구현 상태를 발표하겠습니다."),
    ("발표 흐름", "발표는 문제와 목표, 시스템 설계, 현재 구현, 검증 결과, 그리고 남은 작업 순서로 진행하겠습니다. 5분 발표이므로 최종 기능 전체보다는 중간발표 MVP 범위에 집중하겠습니다."),
    ("프로젝트 개요", "ConnectBox는 같은 LAN 안에 있는 두 Windows PC 사이에서 단일 파일을 직접 전송하는 CLI 도구입니다. 클라우드나 USB를 거치지 않고, 수신 PC를 서버로 두고 송신 PC가 TCP로 접속하는 구조입니다."),
    ("개발 배경 및 문제 정의", "제안발표에서는 새 PC를 세팅하거나 작업 파일을 옮길 때 USB나 클라우드를 반복해서 사용하는 불편함을 문제로 잡았습니다. 같은 네트워크 안에 있어도 직접 전송 수단이 없으면 파일이 불필요하게 우회하게 됩니다."),
    ("중간발표 MVP 범위", "중간발표에서는 GUI나 여러 파일 전송까지 확장하지 않고, TCP 연결과 단일 파일 전송 흐름을 먼저 완성하는 것을 목표로 했습니다. 현재 구현 완료 범위는 단일 파일 전송, 메타데이터 교환, 응답 처리, 진행률 출력, 실행 파일 패키징입니다."),
    ("시스템 전체 구조", "구조는 송신 PC의 클라이언트와 수신 PC의 서버로 나뉩니다. 서버는 포트를 열고 대기하며, 클라이언트는 서버 IP와 포트로 접속해 파일을 보냅니다. 수신된 파일은 서버의 received 폴더에 저장됩니다."),
    ("프로토콜 및 실행 흐름", "TCP는 바이트 스트림이기 때문에 메시지 경계를 직접 정의해야 합니다. 그래서 먼저 4바이트 길이 값을 보내고, 이어서 UTF-8 JSON 메타데이터를 보낸 뒤 파일 본문을 청크 단위로 전송하도록 설계했습니다."),
    ("주요 구현 기능", "코드 구조는 client, server, common, scripts, dist, docs로 나뉩니다. client는 파일 검증과 전송, server는 수신과 저장, common은 프로토콜과 진행률 처리를 담당합니다. scripts에는 테스트 자동화와 더미 파일 생성 기능이 있습니다."),
    ("실행 및 배포 방식", "배포는 GitHub Release v1.0에 ConnectBox_v1.0.zip 형태로 올리는 방식입니다. 주소는 https://github.com/InsuHam0315/ComputerNetwork/releases/tag/v1.0 입니다. 사용자는 압축을 풀고 server.exe와 client.exe를 실행하면 되며, 실행방법.txt에 기본 실행 명령을 함께 정리했습니다."),
    ("검증 결과 및 데모 자료", "현재 로컬 환경에서는 127.0.0.1 기반 전송을 확인했고, 자동 smoke test도 통과했습니다. 이 슬라이드의 왼쪽 영역에는 발표 전에 제가 직접 준비한 서버 콘솔, 클라이언트 콘솔, 수신 폴더 캡처를 넣을 예정입니다."),
    ("구현 중 문제와 해결 과정", "구현하면서 가장 중요한 부분은 TCP에서 메시지 경계가 자동으로 보장되지 않는다는 점이었습니다. 이를 해결하기 위해 length prefix를 사용했습니다. 또한 파일 크기만큼 정확히 수신하도록 하고, 포트 충돌이나 방화벽 이슈는 실행 방법과 체크리스트에 반영했습니다."),
    ("남은 작업 및 기대 효과", "남은 작업은 동일 LAN 두 PC 환경에서의 반복 검증, 체크섬 검증, 폴더 및 다중 파일 전송, GUI 추가입니다. 현재 MVP는 네트워크 수업에서 배운 TCP 소켓 흐름을 실제 파일 전송 프로그램으로 구현했다는 점에 의미가 있습니다. 이상입니다."),
]


def content_types(slide_count: int) -> str:
    overrides = [
        '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>',
        '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>',
        '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>',
        '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>',
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
    ]
    overrides.extend(
        f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(1, slide_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  {''.join(overrides)}
</Types>
"""


def root_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""


def presentation_xml(slide_count: int) -> str:
    sld_ids = "".join(
        f'<p:sldId id="{255 + i}" r:id="rId{i + 1}"/>' for i in range(1, slide_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>
  <p:sldIdLst>{sld_ids}</p:sldIdLst>
  <p:sldSz cx="{SLIDE_W}" cy="{SLIDE_H}" type="wide"/>
  <p:notesSz cx="6858000" cy="9144000"/>
  <p:defaultTextStyle/>
</p:presentation>
"""


def presentation_rels(slide_count: int) -> str:
    rels = ['<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>']
    rels.extend(
        f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>'
        for i in range(1, slide_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  {''.join(rels)}
</Relationships>
"""


def slide_master() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
             xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
             xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="{COLORS['bg']}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>
    <p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
    <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree>
  </p:cSld>
  <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
  <p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
  <p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles>
</p:sldMaster>
"""


def slide_master_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>
"""


def slide_layout() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
             xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
             xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1">
  <p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
  <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>
"""


def slide_layout_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>
"""


def theme_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="ConnectBox">
  <a:themeElements>
    <a:clrScheme name="ConnectBox">
      <a:dk1><a:srgbClr val="1F2933"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>
      <a:dk2><a:srgbClr val="243B53"/></a:dk2><a:lt2><a:srgbClr val="F7F8FA"/></a:lt2>
      <a:accent1><a:srgbClr val="0E7C7B"/></a:accent1><a:accent2><a:srgbClr val="F2A541"/></a:accent2>
      <a:accent3><a:srgbClr val="2F9E44"/></a:accent3><a:accent4><a:srgbClr val="5B677A"/></a:accent4>
      <a:accent5><a:srgbClr val="C92A2A"/></a:accent5><a:accent6><a:srgbClr val="D8DEE8"/></a:accent6>
      <a:hlink><a:srgbClr val="0E7C7B"/></a:hlink><a:folHlink><a:srgbClr val="075E5D"/></a:folHlink>
    </a:clrScheme>
    <a:fontScheme name="Malgun"><a:majorFont><a:latin typeface="Malgun Gothic"/><a:ea typeface="Malgun Gothic"/></a:majorFont><a:minorFont><a:latin typeface="Malgun Gothic"/><a:ea typeface="Malgun Gothic"/></a:minorFont></a:fontScheme>
    <a:fmtScheme name="ConnectBox"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme>
  </a:themeElements>
</a:theme>
"""


def core_props() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>ConnectBox 중간발표</dc:title>
  <dc:creator>2201346 함인수</dc:creator>
  <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
</cp:coreProperties>
"""


def app_props(slide_count: int) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Microsoft PowerPoint</Application>
  <PresentationFormat>Wide</PresentationFormat>
  <Slides>{slide_count}</Slides>
</Properties>
"""


def write_pptx() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    slides = build_slides()
    with zipfile.ZipFile(PPTX_PATH, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types(len(slides)))
        z.writestr("_rels/.rels", root_rels())
        z.writestr("docProps/core.xml", core_props())
        z.writestr("docProps/app.xml", app_props(len(slides)))
        z.writestr("ppt/presentation.xml", presentation_xml(len(slides)))
        z.writestr("ppt/_rels/presentation.xml.rels", presentation_rels(len(slides)))
        z.writestr("ppt/slideMasters/slideMaster1.xml", slide_master())
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", slide_master_rels())
        z.writestr("ppt/slideLayouts/slideLayout1.xml", slide_layout())
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", slide_layout_rels())
        z.writestr("ppt/theme/theme1.xml", theme_xml())
        for idx, slide in enumerate(slides, 1):
            z.writestr(f"ppt/slides/slide{idx}.xml", slide)
            z.writestr(f"ppt/slides/_rels/slide{idx}.xml.rels", rels_for_slide())


def write_script() -> None:
    lines = [
        "# ConnectBox 중간발표 발표 대본",
        "",
        "- 발표 시간: 5분 내외",
        "- 발표 대상: 교수님 및 수강생",
        "- 발표 기준: 중간발표 MVP, 실제 구현 완료 범위와 향후 구현 예정 기능 분리",
        "",
    ]
    for i, (title_text, note) in enumerate(NOTES, 1):
        lines.extend([f"## {i}. {title_text}", "", note, ""])
    SCRIPT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    write_pptx()
    write_script()
    print(PPTX_PATH)
    print(SCRIPT_PATH)


if __name__ == "__main__":
    main()
