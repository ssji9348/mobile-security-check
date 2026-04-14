---
name: security-check
description: 모바일 앱(Android APK / iOS IPA) 보안 점검 20개 항목(정적 16 + 런타임 4)을 실행하고 보고서를 생성합니다.
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash Edit Write Agent TaskCreate TaskUpdate AskUserQuestion
---

# 모바일 앱 보안 점검 스킬

## 사용법
```
/security-check {앱명} [runtime]
```
예:
- `/security-check {앱명}` → 정적 분석만 (항목 1~16)
- `/security-check {앱명} runtime` → 정적 + 런타임 (항목 1~20)

## 인자
- `$ARGUMENTS`: 공백 구분된 인자 목록
  - **첫 번째**: 점검 대상 앱명. 앱명에 공백이 있으면 `runtime` 직전까지가 앱명
  - **마지막 단어가 `runtime`이면**: 런타임 점검(항목 17~20) 포함 실행

## 플랫폼 확인
스킬 실행 시 **항상** AskUserQuestion으로 플랫폼을 확인:

"점검 대상 플랫폼을 선택해주세요."
- **Android** — `apk_list/{앱명}/`에서 smali 기반 정적 분석
- **iOS** — `ipa_list/{앱명}/`에서 Info.plist + strings 분석 (IPA 미추출 시 0.5단계에서 추출)

선택된 플랫폼에 따라 해당 실행 절차(Android / iOS)로 분기

## 실행 절차 — Android (apk_list/)

### 0단계: 사전 확인
1. `security_check_guide.md`를 Read하여 최신 점검 항목 확인
2. `apk_list/{앱명}/` 디렉토리에 디컴파일 결과 존재 여부 확인
3. 없으면 APK 파일을 찾아 `java -jar apktool.jar d` 로 디컴파일

### 1단계: 앱 기본 정보 수집
- `AndroidManifest.xml` → 패키지명, SDK 버전, 컴포넌트 목록
- `apktool.yml` → 버전, 빌드 번호
- smali 파일 수 카운트 (앱 고유 / 전체)

### 2단계: 정적 분석 (16개 항목 병렬 실행)

**Manifest 기반 분석:**
- 항목 2: `uses-permission` 목록
- 항목 7: `android:process`, `android:permission` 속성
- 항목 8: `android:sharedUserId` 존재 여부
- 항목 9: `intent-filter` 과도한 정의, `exported` 컴포넌트

**파일 구조 분석:**
- 항목 1: `assets/`, `unknown/`, `META-INF/` 내 실행 파일, 바이너리 검색

**smali 정적 분석 (병렬 Grep):**
- 항목 3 (악성행위): `ServerSocket`, `Runtime->exec`, `ProcessBuilder`, `Service`, `AlarmManager`, `JobScheduler`
- 항목 4 (외부유출): `http://`, `https://`, `loadUrl`, IP 주소 패턴
- 항목 6 (루팅탐지): `su`, `test-keys`, `RootBeer`, `SafetyNet`, `Build;->TAGS`
- 항목 10 (인증강도): `password`, `Pattern;->compile`, `addJavascriptInterface` (웹뷰 로그인이면 제외)
- 항목 11 (평문저장): `SharedPreferences`, `usesCleartextTraffic`, `Log;->`, `System;->out`, `setMixedContentMode`
- 항목 12 (약한암호): `Cipher`, `MessageDigest`, `DES`, `MD5`, `SHA-1`, `SecretKeySpec`, `KeyStore`
- 항목 13 (기기정보): `TelephonyManager`, `android_id`, `Build;->SERIAL`, `AdvertisingIdClient`
- 항목 14 (다운로드): `DownloadManager`, `PackageInstaller`, `AppUpdateManager`, URL 무결성
- 항목 15 (개인정보동의): `AlertDialog`, `개인정보`, `동의`, `privacy`, `LocationManager`
- 항목 16 (난독화): `.source` 지시어, 클래스명 패턴, 단일문자 클래스

**정적 점검 제외:**
- 항목 5 (자원고갈): 런타임 점검 필요 → `runtime` 인자 시 항목 20에서 점검

### 2.5단계: 런타임 점검 (항목 17~20) — `runtime` 인자 시에만 실행

> **조건**: `$ARGUMENTS`의 마지막 단어가 `runtime`일 때만 실행

**사전 확인:**
1. `platform-tools/adb.exe devices`로 기기 연결 확인. 연결 안 되면 중단 안내
2. AskUserQuestion으로 사용자 승인: "ADB를 통해 앱 삭제/재설치가 진행됩니다. 기기에서 해당 앱의 데이터가 초기화됩니다. 계속하시겠습니까?"
3. 승인 받은 후에만 아래 절차 진행

**항목 17 — 반복 설치 시 오류 발생 (✅ ADB 자동화):**
```bash
ADB="platform-tools/adb.exe"
APK="apk_list/{앱명}/{APK파일}"
PKG="{패키지명}"  # AndroidManifest.xml에서 추출

# 1회차: 제거 → 설치 → 실행 확인
$ADB uninstall $PKG
$ADB install "$APK"
$ADB shell pm list packages | grep $PKG
$ADB shell am start -n $PKG/{SplashActivity}

# 2회차: 제거 → 재설치 → 실행 확인
$ADB uninstall $PKG
$ADB install "$APK"
$ADB shell am start -n $PKG/{SplashActivity}

# 크래시 로그 확인
$ADB logcat -d -s AndroidRuntime:E | grep {패키지_키워드}
```
- 판정: 모든 install/uninstall "Success" + 크래시 로그 없음 → **양호**, 에러 발생 → **취약**

**항목 18 — 앱 삭제 후 안전성 (⚠️ 부분 자동화):**
```bash
# 삭제 전 스냅샷
$ADB shell find /sdcard/ -name '*{패키지키워드}*' 2>/dev/null
$ADB shell ls -la /sdcard/Android/data/$PKG/ 2>&1

# 앱 삭제
$ADB uninstall $PKG

# 삭제 후 잔존 파일 확인
$ADB shell ls -la /sdcard/Android/data/$PKG/ 2>&1
$ADB shell ls -la /sdcard/Android/media/$PKG/ 2>&1
$ADB shell ls -la /sdcard/Android/obb/$PKG/ 2>&1
$ADB shell find /sdcard/ -name '*{패키지키워드}*' 2>/dev/null

# /data/data/ 확인 (루트 필요)
$ADB shell ls /data/data/$PKG/ 2>&1
```
- `/sdcard/` 잔존 파일 없음 → **양호** (부분)
- `/data/data/` 접근 불가 시 → 보고서에 "비루팅 기기로 /data/data/ 미확인" 명시
- 잔존 파일 발견 → **취약**

**항목 20 — 자원고갈 (⚠️ 부분 자동화, 항목 19보다 먼저 실행):**
```bash
# 배터리 통계 리셋
$ADB shell dumpsys batterystats --reset

# 앱 설치 및 실행 (항목 18에서 삭제되었으므로 재설치)
$ADB install "$APK"
$ADB shell am start -n $PKG/{SplashActivity}
```
- AskUserQuestion으로 사용자에게 요청: "앱을 5~10분간 일반적으로 사용해주세요. 완료되면 알려주세요."
- 사용자 완료 응답 후:
```bash
# 트래픽 측정
$ADB shell cat /proc/net/xt_qtaguid/stats | grep {UID}

# 배터리 측정
$ADB shell dumpsys batterystats $PKG
```
- 판정 기준: WebView 앱 10분 사용 기준 >100MB 트래픽 또는 >5% 배터리 → **취약**
- 정상 범위 내 → **양호**

**항목 19 — 기능의 정상동작 (❌ 수동 점검):**
- AskUserQuestion으로 사용자에게 질문:
  "앱 사용 중 다음 항목에서 문제가 있었습니까?
  1. 기능 오동작 또는 미동작
  2. 오탈자
  3. 잘못된 링크
  4. 기타 이상 사항
  (없으면 '없음'으로 답변)"
- 사용자 응답 기반으로 판정:
  - "없음" → **양호**
  - 문제 보고 → **취약** (보고 내용 상세 기록)

**마무리:**
- 앱이 삭제 상태이면 재설치:
```bash
$ADB install "$APK"
```

### 3단계: 보고서 작성
- 출력: `report/{앱명}/security_report.md`
- `runtime` 미포함 시: 앱 정보 → 요약 테이블(16항목) → 항목별 상세 → 종합 의견
- `runtime` 포함 시: 앱 정보 → 요약 테이블(20항목) → 항목별 상세(정적 + 런타임) → 종합 의견
- 런타임 점검 한계 사항은 해당 항목에 명시 (예: 비루팅 /data/data/ 미확인)

### 4단계: 런타임 검증 안내
보고서 작성 후, 추가 런타임 검증이 필요한 항목이 있으면 안내:
- Frida SSL bypass: `frida_js/ssl_bypass.js`
- Burp Suite 프록시 설정 가이드

## 보고서 형식

```markdown
# 보안 점검 보고서 — {앱명}

## 대상 앱 정보
| 항목 | 내용 |
|---|---|
| 앱 이름 | {앱명} |
| 패키지명 | {패키지명} |
| ... | ... |

## 점검 결과 요약

### 정적 분석 (항목 1~16)
| # | 점검 항목 | 결과 | 위험도 |
|---|---|---|---|
| 1 | 비정상 파일/디렉터리 | 양호/주의/취약/점검제외 | —/낮음/중간/높음 |
| ... | ... | ... | ... |
| 16 | 난독화 | ... | ... |

### 런타임 점검 (항목 17~20) — runtime 인자 시에만 포함
| # | 점검 항목 | 결과 | 위험도 |
|---|---|---|---|
| 17 | 반복 설치 시 오류 발생 | 양호/취약 | —/높음 |
| 18 | 앱 삭제 후 안전성 | 양호/취약/부분확인 | —/중간/높음 |
| 19 | 기능의 정상동작 | 양호/취약 | —/중간 |
| 20 | 자원고갈 | 양호/취약 | —/중간/높음 |

## 항목별 상세 분석
### 항목 N — {항목명}
**결과: {판정}**
{분석 내용, 코드 증거, 권고}
- 런타임 항목은 ADB 명령 출력 결과 또는 사용자 응답을 증거로 포함
- 점검 한계가 있으면 명시 (예: "비루팅 기기로 /data/data/ 미확인")

## 종합 의견
{통계, 핵심 취약점 우선 조치 테이블}
```

---

## 실행 절차 — iOS (ipa_list/)

### 0단계: 사전 요구사항 확인

iOS 앱 점검 시작 전, AskUserQuestion으로 다음을 확인:

1. **SSH 접속 정보**: 기기 IP, SSH 포트, 계정, 비밀번호
2. **frida-server 상태**: 기기에서 실행 중인지, 버전
3. **PC frida 버전**: 기기 frida-server와 메이저 버전 일치 여부
4. **SSH 터널**: `ssh -L 27042:127.0.0.1:27042 {계정}@{IP} -p {포트}` 연결 상태

미충족 시 아래 가이드 안내:
- frida 버전 불일치: `pip install frida=={기기버전} frida-tools --upgrade`
- SSH 터널 미설정: 터널 명령 제공
- frida-server 미실행: 기기에서 확인 방법 안내

### 0.5단계: IPA 추출 및 분석 준비

`ipa_list/{앱명}/` 디렉토리에 추출 결과가 없으면:

1. AskUserQuestion으로 **Bundle ID** 확인: "점검 대상 앱의 Bundle ID를 입력해주세요. SSH 터널 상태에서 `frida-ps -H 127.0.0.1:27042 -ai`로 확인 가능합니다."
2. 확인한 Bundle ID로 아래 방법 A → 실패 시 방법 B 순서로 IPA 추출

> 0단계에서 수집한 SSH 접속 정보(IP, 포트, 계정, 비밀번호)를 변수로 사용.
> 모든 명령에서 하드코딩하지 않음.

**방법 A: frida-ios-dump (DRM 해제, 기본)**

실행 전 `tools/frida-ios-dump/dump.py`의 SSH 설정을 사용자 환경에 맞게 임시 수정:
```python
# dump.py 35~38행을 0단계에서 수집한 값으로 수정
User = '{계정}'
Password = '{비밀번호}'
Host = '{IP}'
Port = {SSH포트}
```

SSH 터널 연결 상태에서 실행:
```bash
cd tools/frida-ios-dump
python dump.py {bundle_id}
# 추출된 IPA를 ipa_list/{앱명}/으로 이동
mv {앱명}.ipa ../../ipa_list/{앱명}/
```

실행 후 dump.py를 원본으로 복원:
```python
User = 'root'
Password = 'alpine'
Host = 'localhost'
Port = 2222
```

**방법 A 실패 시 → 방법 B: SSH 직접 복사 (fallback)**
```bash
# 1. 기기에서 .app 경로 찾기
ssh {계정}@{IP} -p {SSH포트} "find /var/containers/Bundle/Application/ -name '*.app' -maxdepth 2" | grep {키워드}

# 2. 기기에서 .app 번들을 zip으로 패키징
ssh {계정}@{IP} -p {SSH포트} "rm -rf /tmp/Payload; mkdir -p /tmp/Payload && cp -r '/var/containers/Bundle/Application/{UUID}/{앱}.app' /tmp/Payload/ && cd /tmp && zip -r {앱명}.ipa Payload/"

# 3. PC로 전송
scp -P {SSH포트} {계정}@{IP}:/tmp/{앱명}.ipa ipa_list/{앱명}/
```

> **주의**: 방법 B는 DRM이 해제되지 않은 상태로 복사됨.
> `strings` 분석은 가능하지만, 암호화된 바이너리일 경우 일부 문자열이 누락될 수 있음.

**추출 후 IPA 압축 해제:**
```bash
cd ipa_list/{앱명}
unzip {앱명}.ipa
# → Payload/{앱}.app/ 하위에 바이너리, plist, 리소스 등
```

### 1단계: 앱 기본 정보 수집 (iOS)
- `Payload/{앱}.app/Info.plist` → Bundle ID, 버전, 빌드, MinimumOSVersion
- `Payload/{앱}.app/embedded.mobileprovision` → 프로비저닝 정보 (있을 경우)
- 바이너리 파일 크기, 아키텍처 확인

### 2단계: iOS 정적 분석 (16개 항목)

> plist는 Read, 바이너리는 `strings` 명령으로 분석. 검색 대상: `ipa_list/{앱명}/Payload/{앱}.app/`

**Info.plist 기반 분석:**
- 항목 2 (권한): `NS*UsageDescription` 키 목록 (카메라, 위치, 사진 등)
- 항목 7 (ID 값): App Groups, Keychain Access Groups (entitlements)
- 항목 8 (UID 공유): App Groups entitlement 존재 여부
- 항목 9 (URL Scheme): `CFBundleURLTypes`, Universal Links 설정
- 항목 11 (ATS): `NSAppTransportSecurity` → `NSAllowsArbitraryLoads` 확인

**파일 구조 분석:**
- 항목 1: `.app/` 내 비정상 파일 (실행 바이너리, 스크립트, 숨김 파일)
- Frameworks/ 내 서드파티 프레임워크 목록

**바이너리 문자열 분석 (`strings` 명령, 병렬):**
```bash
strings "ipa_list/{앱명}/Payload/{앱}.app/{바이너리}" > /tmp/{앱명}_strings.txt
```
- 항목 3 (악성행위): `NSTask`, `posix_spawn`, `dlopen`, `system(`, 백그라운드 모드
- 항목 4 (외부유출): `http://`, `https://`, IP 주소 패턴, 하드코딩 URL
- 항목 6 (탈옥탐지): `/Applications/Cydia`, `/usr/sbin/sshd`, `/bin/bash`, `canOpenURL`, `stat("/`
- 항목 10 (인증강도): `password`, `UITextField`, `isSecureTextEntry`, WebView 로그인 확인
- 항목 11 (평문저장): `NSUserDefaults`, `NSLog`, `print(`, `CFPreferences`, `SQLite`
- 항목 12 (약한암호): `kCCAlgorithmDES`, `kCCAlgorithm3DES`, `CC_MD5`, `CC_SHA1`, `SecKeyCreateEncryptedData`
- 항목 13 (기기정보): `identifierForVendor`, `advertisingIdentifier`, `deviceName`, `systemVersion`
- 항목 14 (다운로드): `NSURLSession`, `URLSessionDownloadTask`, 외부 URL 무결성
- 항목 15 (개인정보동의): `CLLocationManager`, `개인정보`, `동의`, `privacy`, `UIAlertController`
- 항목 16 (난독화): 심볼 테이블 존재 여부, 클래스/메서드명 패턴 (원본명 유지 vs 난독화)

**정적 점검 제외:**
- 항목 5 (자원고갈): 런타임 점검 필요 → `runtime` 인자 시 항목 20에서 점검

### 2.5단계: iOS 런타임 점검 (항목 17~20) — `runtime` 인자 시에만

> **조건**: `runtime` 인자 + SSH/frida 사전 요구사항 충족 시

**사전 확인:**
1. SSH 접속 가능 여부 확인
2. AskUserQuestion으로 승인: "SSH를 통해 앱 삭제/재설치가 진행됩니다. 계속하시겠습니까?"

**항목 17 — 반복 설치 시 오류 (SSH 기반):**
- 사용자에게 기기에서 앱 삭제 → 재설치 → 삭제 → 재설치 수행 요청
- 각 단계 결과를 AskUserQuestion으로 수집

**항목 18 — 앱 삭제 후 안전성 (SSH 기반):**
```bash
# SSH에서 실행 (root 권한)
# 삭제 전 스냅샷
find /var/mobile/Containers/Data/Application/ -name "*{키워드}*" 2>/dev/null

# 사용자에게 앱 삭제 요청 후
# 삭제 후 잔존 파일 확인
find /var/mobile/Containers/Data/Application/ -name "*{키워드}*" 2>/dev/null
find /var/mobile/Documents/ -name "*{키워드}*" 2>/dev/null
ls -la /tmp/*{키워드}* 2>/dev/null
```
- iOS는 탈옥 기기이므로 `/var/mobile/` 전체 접근 가능
- 잔존 파일 없음 → **양호**, 발견 → **취약**

**항목 20 — 자원고갈 (부분 자동화):**
- 사용자에게 앱 5~10분 사용 요청
- 사용 전후 배터리 레벨 확인: 사용자에게 설정 > 배터리 확인 요청

**항목 19 — 기능 정상동작 (수동):**
- AskUserQuestion으로 사용자에게 동일 질문 (오동작, 오탈자, 잘못된 링크, 기타)

### 3단계: 보고서 작성 (iOS)
- 출력: `report/{앱명}/security_report.md`
- 형식은 Android와 동일하되, iOS 특화 정보 포함:
  - 플랫폼: iOS
  - Bundle ID (패키지명 대신)
  - MinimumOSVersion (minSdkVersion 대신)
  - ATS 설정 (usesCleartextTraffic 대신)

### 4단계: 런타임 검증 안내 (iOS)
- Frida SSL bypass: `frida_js/ios_ssl_bypass.js`
- Frida 탈옥 탐지 우회: `frida_js/ios_jailbreak_bypass.js`
- Burp Suite 프록시 설정 (Wi-Fi 프록시 또는 SSH 터널)
