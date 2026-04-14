## 개요

- 모바일 어플리케이션에 대한 점검 진행
- 점검은 프로젝트 CLAUDE.md의 행동 규칙을 준수하여 진행
- 정적 분석(항목 1~16):
  - Android: smali로 해제된 앱에 대해 점검 진행
  - iOS: IPA 추출 후 Info.plist + strings 바이너리 분석
  - 진행하지 못할 시, 별도 명시
- 런타임 점검(항목 17~20): Android는 ADB, iOS는 SSH/frida 기반. `runtime` 인자 필요

## 정적 점검 항목


| # | 점검항목 | 설명 |
| --- | ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| 1 | 앱 설치 전후 비정상적인 파일 및 디렉터리 설치여부 | |
| 2 | 불필요하거나 과도한 권한 설정 | |
| 3 | 임의기능 등 악성행위 기능 존재 | 백그라운드에서 알 수 없는 포트가 Listen 되는지, 명시적인 기능 외 백그라운드로 실행되는 의심스러운 행위가 있는지 |
| 4 | 정보 외부 유출 | 앱 서버 또는 업데이트 서버 등 허가된 주소 이외의 주소로 정보 전송이 발생하는 경우 |
| 5 | 자원고갈 | 비정상적인 배터리 사용 유무로 점검 제외 |
| 6 | 루팅 및 탈옥 기기에서의 정상 동작 | |
| 7 | ID 값의 변경 | 설치된 앱의 설치 권한과 실행 권한이 다를 경우 |
| 8 | 동일키로 서명된 서로 다른 앱 간의 UID 공유(Android) | AndroidManifest.xml 파일 내 SharedUserId 설정 여부 |
| 9 | 인텐트 권한의 올바른 설정 | AndroidManifest.xml 내부의 intent-filter 항목에 과도하게 많은 필터링 정의가 되어 있는 경우 |
| 10 | 인증 정보 생성 강도 적절성 | 안전하지 않은 비밀번호 생성 규칙으로 비밀번호를 생성, 변경할 수 있는 경우, 단 웹 뷰 형태로 로그인이 진행되는 경우 제외 |
| 11 | 중요 정보의 평문 저장 및 전송 | 모바일 기기 내부 파일에서 중요정보를 검색했을 때, 평문으로 검색 가능 또는 로그인 등 전송되는 중요정보가 평문으로 전송 |
| 12 | 중요정보 저장 및 전송 시 취약한 암호 알고리즘 적용 | - 로그인 시 사용한 id, pwd를 검색했을 때, 평문으로 검색이 가능한 경우 - 112비트 미만의 키 길이를 갖는 약한 암호화를 사용할 경우(대칭키) - 2048비트 미만의 키 길이를 갖는 약한 암호화를 사용할 경우(공개키) |
| 13 | 기타 중요정보의 평문 저장 및 전송 | 기타 중요정보(IMEI,IMSI)가 평문으로 전송/검색이 가능할 경우(HTTPS 전송은 제외) |
| 14 | 파일 다운로드 시 외부 주소 변조 및 파일 무결성 우회 | - 앱 설정 파일 또는 실행 파일에 포함된 서버주소에 허가되지 않은 다른 주소가 포함되어 있는 경우 - 기본 설정된 서버주소 변경 및 삭제 시 무결성 오류 발생 여부 - 기본 설정된 서버 주소 변경 및 삭제 시 정상 동작 시 취약 |
| 15 | 개인정보 및 개인위치 정보 수집 및 활용에 대한 동의 | 앱 실행 시 사용자에게 개인정보 및 개인위치정보를 사용한다는 사전 동의 알럿이 출력되지 않는 경우 |
| 16 | 난독화 | |


## iOS 정적 분석 매핑

| # | 점검항목 | Android 분석 대상 | iOS 분석 대상 |
|---|---|---|---|
| 1 | 비정상 파일 | assets/, unknown/ | .app/ 내 비정상 바이너리 |
| 2 | 과도한 권한 | uses-permission | NS*UsageDescription (Info.plist) |
| 3 | 악성행위 | ServerSocket, Runtime->exec | NSTask, posix_spawn, dlopen |
| 4 | 외부유출 | http://, loadUrl | http://, NSURLSession |
| 6 | 루팅/탈옥 탐지 | su, RootBeer | /Applications/Cydia, canOpenURL |
| 7 | ID 값 변경 | android:process, android:permission | App Groups (entitlements) |
| 8 | UID 공유 | sharedUserId | App Groups entitlement |
| 9 | 인텐트/URL Scheme | intent-filter, exported | CFBundleURLTypes, Universal Links |
| 10 | 인증강도 | password, addJavascriptInterface | UITextField, isSecureTextEntry |
| 11 | 평문저장/전송 | SharedPreferences, usesCleartextTraffic | NSUserDefaults, NSAllowsArbitraryLoads (ATS) |
| 12 | 약한암호 | Cipher, DES, MD5 | kCCAlgorithmDES, CC_MD5, CC_SHA1 |
| 13 | 기기정보 | TelephonyManager, android_id | identifierForVendor, advertisingIdentifier |
| 14 | 다운로드 무결성 | DownloadManager, PackageInstaller | NSURLSession, URLSessionDownloadTask |
| 15 | 개인정보동의 | AlertDialog, LocationManager | UIAlertController, CLLocationManager |
| 16 | 난독화 | .source 지시어, 클래스명 패턴 | 심볼 스트리핑, 클래스/메서드명 패턴 |

## 런타임 점검 항목 (항목 17~20)

Android는 ADB, iOS는 SSH 기반. `/security-check {앱명} runtime` 으로 실행.

| # | 점검항목 | 설명 |
| --- | --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 17 | 반복 설치 시 오류 발생 | 앱 설치, 삭제, 재설치 시도 중 에러가 발생하면 취약 |
| 18 | 앱 삭제 후 안전성 | 앱 삭제 전후로 아래와 같으면 취약한 것으로 판단 (Android) /data/data 디렉토리나 내부에 잔존 파일이 존재 (Android) sd카드 사용 시 /sdcard 디렉토리 내부에 잔존 파일이 존재 - /var/mobile/Applications/(iOS 7 이하) - /var/mobile/Containers/Data/Application/ (iOS 8 이상) 디렉토리 내부에 잔존 파일이 존재 |
| 19 | 기능의 정상동작 | 기능 오동작, 미동작, 오탈자, 잘못된 링크 등이 발견될 경우 취약 |
| 20 | 자원고갈 | 앱 실행 시 배터리/트래픽 사용량이 과도하게 증가하게 되면 취약 |


