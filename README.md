# 모바일 앱 보안 점검 자동화 템플릿

Claude Code를 활용하여 Android APK / iOS IPA 보안 점검 20개 항목을 자동으로 수행하고 보고서를 생성합니다.

## 빠른 시작 (3단계)

### 1. 저장소 클론 + 도구 배치

```bash
git clone https://github.com/ssji9348/mobile-security-check mobile-security-check
cd mobile-security-check
```

아래 도구를 직접 다운로드하여 배치합니다:

| 도구 | 배치 위치 | 용도 | 필수 여부 |
|---|---|---|---|
| APKTool | `apktool.jar` (루트) | Android APK 디컴파일 | Android 점검 시 필수 |
| ADB (platform-tools) | `platform-tools/` | Android 런타임 점검 | runtime 옵션 시 필수 |
| frida-ios-dump | `tools/frida-ios-dump/` | iOS IPA 추출 | iOS 점검 시 필요 |

- APKTool: https://apktool.org/
- ADB: https://developer.android.com/tools/releases/platform-tools
- frida-ios-dump: https://github.com/AloneMonkey/frida-ios-dump

### 2. 점검 대상 앱 배치

**Android:**
```
apk_list/{앱이름}/
└── {파일}.apk
```

**iOS:**
```
ipa_list/{앱이름}/
└── {파일}.ipa    ← IPA가 없으면 스킬 실행 시 frida-ios-dump로 자동 추출
```

- 폴더명이 점검 시 앱 이름으로 사용됩니다
- 여러 앱을 점검하려면 각각 폴더를 만들어 배치하세요

### 3. 점검 실행

```bash
# Claude Code 시작
claude

# 정적 분석만 (항목 1~16)
> /security-check {앱이름}

# 정적 + 런타임 (항목 1~20)
> /security-check {앱이름} runtime
```

실행 시 플랫폼(Android/iOS)을 선택하면, 해당 플랫폼에 맞는 분석이 자동 수행됩니다.

보고서가 `report/{앱이름}/security_report.md`에 자동 생성됩니다.

## 점검 항목 (20개)

### 정적 분석 (항목 1~16)

| # | 항목 | Android | iOS |
|---|---|---|---|
| 1 | 비정상 파일/디렉터리 | 파일 구조 스캔 | .app/ 스캔 |
| 2 | 과도한 권한 설정 | Manifest | Info.plist |
| 3 | 악성행위 기능 존재 | smali grep | strings grep |
| 4 | 정보 외부 유출 | smali grep | strings grep |
| 5 | 자원고갈 | 런타임(항목 20) | 런타임(항목 20) |
| 6 | 루팅/탈옥 기기 탐지 | smali grep | strings grep |
| 7 | ID 값의 변경 | Manifest | entitlements |
| 8 | UID 공유 | Manifest | App Groups |
| 9 | 인텐트/URL Scheme 설정 | Manifest | Info.plist |
| 10 | 인증 정보 생성 강도 | smali grep | strings grep |
| 11 | 중요 정보 평문 저장/전송 | smali grep | plist + strings |
| 12 | 약한 암호 알고리즘 | smali grep | strings grep |
| 13 | 기기정보 평문 저장/전송 | smali grep | strings grep |
| 14 | 다운로드 주소 변조/무결성 | smali grep | strings grep |
| 15 | 개인정보 수집 동의 | smali grep | strings grep |
| 16 | 난독화 | smali grep | 심볼 분석 |

### 런타임 점검 (항목 17~20)

`runtime` 인자를 추가하세요. Android는 ADB, iOS는 SSH 기기 연결이 필요합니다.

| # | 항목 | 자동화 수준 |
|---|---|---|
| 17 | 반복 설치 시 오류 | Android: 완전 자동 / iOS: 수동 |
| 18 | 앱 삭제 후 안전성 | 부분 자동 |
| 19 | 기능 정상동작 | 수동 (Q&A) |
| 20 | 자원고갈 | 부분 자동 |

## iOS 점검 사전 요구사항

iOS 앱 점검을 위해 아래 환경이 필요합니다:

- 탈옥 기기에서 SSH 접속 가능 (계정, IP, 포트)
- frida-server가 기기에서 실행 중
- PC의 frida-tools와 기기 frida-server의 메이저 버전 일치
- SSH 터널: `ssh -L 27042:127.0.0.1:27042 {계정}@{IP} -p {포트}`
- frida 버전 불일치 시: `pip install frida=={기기버전} frida-tools --upgrade`

## 폴더 구조

```
mobile-security-check/
├── README.md                     ← 이 파일
├── CLAUDE.md                     ← Claude Code 프로젝트 설정
├── security_check_guide.md       ← 20개 점검 항목 정의서
├── apktool.jar                   ← APKTool (직접 배치)
├── platform-tools/               ← ADB (직접 배치)
├── tools/
│   └── frida-ios-dump/           ← iOS IPA 추출 (직접 배치)
├── .claude/
│   ├── settings.local.json       ← 명령 권한 화이트리스트
│   └── skills/
│       └── security-check/
│           └── SKILL.md          ← /security-check 스킬 정의
├── apk_list/                     ← Android APK 배치
├── ipa_list/                     ← iOS IPA 배치
├── report/                       ← 보고서 출력
└── frida_js/                     ← Frida 스크립트 (런타임 검증용)
```

## 자주 묻는 질문

**Q: 디컴파일/IPA 추출을 미리 해야 하나요?**
A: 아니요. `/security-check`를 실행하면 자동으로 확인하고 필요시 실행합니다.

**Q: 런타임 점검 없이 정적 분석만 할 수 있나요?**
A: 네. `runtime` 인자를 빼면 정적 분석(항목 1~16)만 실행합니다.

**Q: ADB/SSH 기기가 없으면?**
A: 정적 분석은 기기 없이 가능합니다. 런타임 점검(항목 17~20)만 기기가 필요합니다.

**Q: 여러 앱을 한 번에 점검할 수 있나요?**
A: 현재는 앱 1개씩 실행합니다. 각 앱 폴더를 만들고 순차 실행하세요.

**Q: 보고서 형식을 커스터마이징하고 싶어요.**
A: `.claude/skills/security-check/SKILL.md`의 "보고서 형식" 섹션을 수정하세요.

**Q: Android frida와 iOS frida 버전이 달라요.**
A: 전환 시 `pip install frida=={버전} frida-tools --upgrade`로 재설치하거나, Python venv를 분리하세요.

## Frida 런타임 검증 (선택)

정적 분석에서 발견한 취약점을 런타임에서 확인하려면:

```bash
# Android SSL 인증서 검증 우회
frida -U -f {패키지명} -l frida_js/ssl_bypass_template.js

# iOS SSL 우회 (별도 스크립트 필요)
frida -U -f {Bundle_ID} -l frida_js/ios_ssl_bypass.js
```

Burp Suite 프록시와 함께 사용하면 실제 API 트래픽을 캡처할 수 있습니다.
