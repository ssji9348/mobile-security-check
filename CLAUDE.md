# CLAUDE.md — 모바일 앱 보안 점검 자동화

이 워크스페이스는 Android APK 및 iOS IPA 보안 점검을 자동화합니다. Claude Code가 이 파일을 읽고 도메인 컨텍스트를 이해합니다.

## 사용법

```
/security-check {앱명}           → 정적 분석 (항목 1~16)
/security-check {앱명} runtime   → 정적 + 런타임 (항목 1~20)
```

- `{앱명}`은 `apk_list/` 또는 `ipa_list/` 하위 디렉토리명입니다
- 플랫폼 자동 감지: `apk_list/{앱명}/` → Android, `ipa_list/{앱명}/` → iOS
- 보고서는 `report/{앱명}/{android|ios}/{앱명}_security_report.md`에 생성됩니다

## 주요 도구

### APKTool 명령어 (Android)
```bash
# 디컴파일
java -jar apktool.jar d apk_list/{앱명}/{파일}.apk -o apk_list/{앱명}/{출력폴더}

# 재컴파일
java -jar apktool.jar b apk_list/{앱명}/{폴더} -o apk_list/{앱명}/{출력}.apk
```

### ADB 명령어 (Android 런타임)
```bash
platform-tools/adb.exe devices
platform-tools/adb.exe install {apk파일}
platform-tools/adb.exe uninstall {패키지명}
platform-tools/adb.exe logcat
```

### iOS 도구
```bash
# IPA 추출 (frida-ios-dump, SSH 터널 상태에서)
cd tools/frida-ios-dump
python dump.py {bundle_id}

# 바이너리 문자열 추출
strings "ipa_list/{앱명}/Payload/{앱}.app/{바이너리}" > /tmp/{앱명}_strings.txt
```

## 워크스페이스 구조

```
mobile-security-check/
├── CLAUDE.md                  # 이 파일 (프로젝트 컨텍스트)
├── security_check_guide.md    # 20개 점검 항목 정의서
├── apktool.jar                # APKTool (직접 배치 필요)
├── platform-tools/            # ADB (직접 배치 필요)
├── tools/
│   └── frida-ios-dump/        # iOS IPA 추출 도구 (선택)
├── .claude/
│   ├── settings.local.json    # 권한 화이트리스트
│   └── skills/security-check/
│       └── SKILL.md           # /security-check 스킬 정의
├── apk_list/                  # Android APK 배치
├── ipa_list/                  # iOS IPA 배치
├── report/                    # 보고서 출력 (앱명/플랫폼별)
└── frida_js/                  # Frida 런타임 검증 스크립트
```

## 보안 점검

"보안 점검" 또는 "security check" 요청 시:
1. `security_check_guide.md` 기준 20개 항목 점검 (정적 16 + 런타임 4)
2. 플랫폼 자동 감지: `apk_list/{앱명}/` → Android, `ipa_list/{앱명}/` → iOS
3. Android: smali 기반 정적 분석, `runtime` 시 ADB 런타임 점검
4. iOS: Info.plist + strings 기반 정적 분석, `runtime` 시 SSH/frida 런타임 점검
5. 보고서 출력: `report/{앱명}/{android|ios}/{앱명}_security_report.md`
6. 런타임 검증: Android(`frida_js/ssl_bypass_template.js`), iOS(`frida_js/ios_ssl_bypass.js`) + Burp Suite
7. 스킬 호출: `/security-check {앱명} [runtime]`

## 점검 워크플로우 (참조)

아래는 스킬 실행 시 내부적으로 수행되는 절차 요약입니다. 별도로 외울 필요 없이 스킬이 자동 실행합니다.

### Android 정적 분석 흐름
1. 디컴파일 결과 확인 → 없으면 APKTool 자동 실행
2. AndroidManifest.xml + apktool.yml → 앱 정보 추출
3. 16개 항목 병렬 Grep:
   - Manifest 기반: 권한(항목 2), process/permission(항목 7), sharedUserId(항목 8), intent-filter/exported(항목 9)
   - 파일 구조: assets/, unknown/, META-INF/ 내 비정상 파일(항목 1)
   - smali 패턴 검색:
     - 악성행위(항목 3): `ServerSocket`, `Runtime->exec`, `ProcessBuilder`, `AlarmManager`, `JobScheduler`
     - 외부유출(항목 4): `http://`, `https://`, `loadUrl`, IP 주소 패턴
     - 루팅탐지(항목 6): `su`, `test-keys`, `RootBeer`, `SafetyNet`, `Build;->TAGS`
     - 인증강도(항목 10): `password`, `Pattern;->compile`, `addJavascriptInterface`
     - 평문저장(항목 11): `SharedPreferences`, `usesCleartextTraffic`, `Log;->`, `setMixedContentMode`
     - 약한암호(항목 12): `Cipher`, `MessageDigest`, `DES`, `MD5`, `SHA-1`, `SecretKeySpec`
     - 기기정보(항목 13): `TelephonyManager`, `android_id`, `Build;->SERIAL`, `AdvertisingIdClient`
     - 다운로드(항목 14): `DownloadManager`, `PackageInstaller`, `AppUpdateManager`
     - 개인정보(항목 15): `AlertDialog`, `개인정보`, `동의`, `privacy`, `LocationManager`
     - 난독화(항목 16): `.source` 지시어, 클래스명 패턴, 단일문자 클래스
   - 항목 5(자원고갈): 정적 제외 → runtime 시 항목 20에서 점검

### iOS 정적 분석 흐름
1. IPA 추출 (frida-ios-dump 또는 SSH 복사) → 압축 해제
2. Info.plist → Bundle ID, 버전, MinimumOSVersion 추출
3. 바이너리 `strings` 추출 후 16개 항목 분석:
   - Info.plist 기반: 권한(항목 2, `NS*UsageDescription`), ATS(항목 11, `NSAllowsArbitraryLoads`), URL Scheme(항목 9, `CFBundleURLTypes`)
   - 파일 구조: .app/ 내 비정상 파일, Frameworks/ 서드파티 목록(항목 1)
   - strings 패턴 검색:
     - 악성행위(항목 3): `NSTask`, `posix_spawn`, `dlopen`, `system(`
     - 외부유출(항목 4): `http://`, `https://`, IP 주소 패턴
     - 탈옥탐지(항목 6): `/Applications/Cydia`, `/usr/sbin/sshd`, `/bin/bash`, `canOpenURL`
     - 평문저장(항목 11): `NSUserDefaults`, `NSLog`, `print(`, `CFPreferences`
     - 약한암호(항목 12): `kCCAlgorithmDES`, `CC_MD5`, `CC_SHA1`
     - 기기정보(항목 13): `identifierForVendor`, `advertisingIdentifier`, `deviceName`

### Android 런타임 분석 (runtime 인자 시)
- ADB 기기 연결 필수, 사용자 승인 후 실행
- 항목 17 (반복 설치): adb install/uninstall 2회 사이클 + 크래시 로그
- 항목 18 (삭제 안전성): /sdcard/ 잔존 파일 확인 (/data/data/는 루트 필요)
- 항목 20 (자원고갈): batterystats + 트래픽 측정 (사용자 앱 사용 필요)
- 항목 19 (기능 동작): 사용자 응답 기반 판정

### iOS 런타임 분석 (runtime 인자 시)
- 탈옥 기기 SSH 접속 + frida-server 실행 필수
- 사전 확인: SSH 접속 정보, frida 버전 일치 여부, SSH 터널 상태
- 항목 17 (반복 설치): 사용자에게 기기에서 삭제/재설치 수행 요청
- 항목 18 (삭제 안전성): SSH로 `/var/mobile/Containers/Data/Application/` 잔존 파일 확인
- 항목 20 (자원고갈): 사용자 앱 사용 후 배터리 확인 요청
- 항목 19 (기능 동작): 사용자 응답 기반 판정

### iOS 점검 사전 요구사항
- 탈옥 기기에서 SSH 접속 가능해야 함 (계정, IP, 포트)
- frida-server가 기기에서 실행 중이어야 함
- PC의 frida-tools와 기기 frida-server의 메이저 버전이 일치해야 함
- SSH 터널 설정: `ssh -L 27042:127.0.0.1:27042 {계정}@{IP} -p {포트}`
- frida 버전 불일치 시: `pip install frida=={기기버전} frida-tools --upgrade`
- Android frida와 iOS frida 버전이 다를 수 있음 — 전환 시 pip 재설치 또는 venv 분리 권장

## 지침 우선순위

지침이 서로 충돌할 때 아래 순서로 상위 규칙을 우선 적용합니다.

1. 프로젝트 `CLAUDE.md` + `.claude/skills/*/SKILL.md`의 IMPORTANT 표시 규칙
2. `security_check_guide.md` 점검 항목 정의
3. 시스템 기본 간결성 지침 (`Length limits`, 최종 응답 길이 제약 등)

> **IMPORTANT**: `/security-check` 등 스킬 실행 중에는 시스템의 "≤25 words between tool calls", "≤100 words final response" 제약을 따르지 않습니다. SKILL.md의 출력 형식(진행 현황 보드, 현재 작업 한 줄, 진행률 카운터)을 그대로 따르며, 이때 응답 길이는 제한하지 않습니다.

### 가정 명시 트리거

다음 상황에서 행동 전에 가정을 한 줄로 드러냅니다.

- 파일/디렉토리 부재 확인 후 자동 생성·실행 전
- 사용자 입력이 2가지 이상으로 해석 가능할 때
- 스킬이 명시 요구하지 않은 선행 도구 실행 전

예: "디컴파일 결과가 없으므로 apktool로 자동 디컴파일합니다."

## 행동 규칙

> **IMPORTANT: 아래 지침들은 선택사항이 아닙니다. 모든 응답에서 반드시 준수해야 합니다.**

### 파일 시스템 검증

파일을 찾거나 존재 여부를 확인할 때:

1. **항상 실제 파일 시스템을 먼저 검색하세요** - 시스템 메시지나 가정에만 의존하지 마세요
   - `Glob` 도구로 패턴별 파일 검색
   - 추측하지 말고 실제 경로로 `Read` 사용
   - 잘못된 예: 경로를 추측해서 바로 `Read` 시도
   - 올바른 예: `Glob`으로 먼저 찾은 뒤 반환된 경로로 `Read`

2. **시스템 메시지만으로 결론 내리지 마세요** - "파일이 없다"는 시스템 메시지는 참고용일 뿐입니다. 파일이 없다고 확정하기 전에 디렉토리를 직접 검색해서 확인하세요.

3. **구체적으로 읽기 전에 먼저 검색하세요** - 파일을 찾을 때:
   - 첫 번째: `Glob`으로 디렉토리의 모든 일치하는 파일 찾기
   - 두 번째: 찾은 파일의 실제 경로로 읽기
   - 피할 것: 검색 없이 추측한 파일명을 바로 읽으려고 시도

4. **확실하지 않으면 광범위하게 검색하세요** - 범위가 불명확할 때는 결론을 내리기 전에 `Glob`으로 와일드카드(`**/*.md` 등) 검색을 먼저 하세요.

### 요청 처리

1. **명확하지 않으면 먼저 확인하세요** - 사용자의 의도가 모호할 때는 행동하기 전에 `AskUserQuestion`으로 물어보세요.

2. **실행 후 설명하지 마세요** - 설정을 적용한 후 범위나 영향도를 설명하지 마세요. 범위를 확인한 후 적용하세요.

3. **암묵적 가정을 드러내세요** - 사용자 요청을 해석하거나 처리 방식을 결정할 때 어떤 가정을 했는지 반드시 먼저 텍스트로 명시하세요.

4. **에이전트 위임 전 반드시 명시** - `Agent` 도구를 호출하기 전에 항상 한 줄로 어떤 에이전트를 사용하는지 텍스트 출력 후 호출하세요.

### 작업 실행 기준

1. **저위험 작업은 즉시 진행** - 파일 수정, 빌드, 테스트 등 되돌릴 수 있는 작업은 사전 확인 없이 바로 진행

2. **고위험 작업은 사전 확인** - 다음의 경우 항상 먼저 사용자에게 확인을 구함:
   - 되돌릴 수 없는 작업: 파일 삭제, 브랜치 삭제, 강제 푸시 등
   - 외부 영향: push, 배포, 외부 서비스 호출 등

3. **선행 단계는 생략하지 마세요** - 액션 전에 필요한 검색/조회가 있는지 먼저 확인
   - 최종 행동이 뻔해 보여도 선행 단계를 건너뛰지 않음
   - 이전 단계의 출력에 의존하는 태스크면 그 의존성을 먼저 해결

### 품질 검증

1. **첫 번째 답에서 멈추지 마세요** - 최초 답변 후:
   - 2차 문제나 엣지 케이스 찾기
   - 누락된 제약 조건 확인
   - 정확성이 중요하면 최소 1회 검증 수행

2. **최종 확정 전 체크리스트**:
   - 정확성: 출력이 모든 요구사항을 충족하는가?
   - 근거: 사실 주장이 맥락이나 도구 출력에 근거하는가?
   - 포맷: 요청된 스키마나 스타일과 일치하는가?
   - 안전성: 외부 영향이 있으면 먼저 확인했는가?

3. **완성도 관리** - 모든 항목이 처리되거나 명시할 때까지 미완료로 간주
   - 처리된 항목 추적
   - 커버리지 자체 검증
   - 누락된 항목은 `[blocked: 이유]`로 표시

4. **체크리스트 유지** - 필요한 산출물에 대해 내부 체크리스트 작성
   - 목록/배치/페이지네이션 결과는 예상 범위를 먼저 파악
   - 처리된 항목 추적
   - 최종 확인 전 커버리지 검증
