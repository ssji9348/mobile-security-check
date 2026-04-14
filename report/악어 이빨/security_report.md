# 보안 점검 보고서 — 악어 이빨 (Croco Roulette)

> 점검일: 2026-04-14
> 점검 범위: 정적 분석 (항목 1~16)
> 플랫폼: Android

---

## 대상 앱 정보

| 항목 | 내용 |
|---|---|
| 앱 이름 | Croco Roulette (악어 이빨) |
| 패키지명 | com.OVJECT.CrocoR |
| 버전명 | 1.1.12 |
| 버전 코드 | 1001012 |
| minSdkVersion | 16 (Android 4.1 Jelly Bean) |
| targetSdkVersion | 30 (Android 11) |
| 게임 엔진 | GameMaker Studio (YoYo Games Runner) |
| 주요 라이브러리 | Google Mobile Ads SDK, androidx.work, Google UMP |
| 서명 | GOOGPLAY.RSA (Google Play 배포 서명) |
| allowBackup | false |
| smali 파일 수 | 전체 7,754개 / 앱 고유 394개 |

---

## 점검 결과 요약

### 정적 분석 (항목 1~16)

| # | 점검 항목 | 결과 | 위험도 |
|---|---|---|---|
| 1 | 앱 설치 전후 비정상적인 파일 및 디렉터리 | 양호 | — |
| 2 | 불필요하거나 과도한 권한 설정 | 양호 | — |
| 3 | 임의기능 등 악성행위 기능 존재 | 양호 | — |
| 4 | 정보 외부 유출 | 양호 | — |
| 5 | 자원고갈 | 점검 제외 | — |
| 6 | 루팅 및 탈옥 기기에서의 정상 동작 | 취약 | 낮음 |
| 7 | ID 값의 변경 | 양호 | — |
| 8 | 동일키로 서명된 서로 다른 앱 간의 UID 공유 | 양호 | — |
| 9 | 인텐트 권한의 올바른 설정 | 양호 | — |
| 10 | 인증 정보 생성 강도 적절성 | 점검 제외 | — |
| 11 | 중요 정보의 평문 저장 및 전송 | 주의 | 낮음 |
| 12 | 중요정보 저장 및 전송 시 취약한 암호 알고리즘 적용 | 양호 | — |
| 13 | 기타 중요정보의 평문 저장 및 전송 | 주의 | 낮음 |
| 14 | 파일 다운로드 시 외부 주소 변조 및 파일 무결성 우회 | 양호 | — |
| 15 | 개인정보 및 개인위치 정보 수집 및 활용에 대한 동의 | 양호 | — |
| 16 | 난독화 | 취약 | 낮음 |

**요약: 취약 2건, 주의 2건, 점검 제외 2건, 양호 10건**

---

## 항목별 상세 분석

### 항목 1 — 앱 설치 전후 비정상적인 파일 및 디렉터리

**결과: 양호**

`assets/`, `lib/`, `unknown/`, `META-INF/` 내 파일을 확인한 결과 모두 정상 범위입니다.

| 경로 | 파일 | 판정 |
|---|---|---|
| assets/ | game.droid | GameMaker Studio 게임 데이터 (정상) |
| assets/ | googlemobileads.ext, consentform.html | 광고 SDK 관련 (정상) |
| assets/ | options.ini | 앱 빌드 설정 (정상, 단 개발자 PC 경로 포함 — 아래 참조) |
| lib/ | libyoyo.so, libc++_shared.so, liboboe.so | GameMaker Studio 표준 네이티브 라이브러리 |
| unknown/META-INF/ | play-services-*.properties | Google Play Services 메타 파일 (정상) |

**비고:** `assets/options.ini`에 빌드 환경의 macOS NDK 절대 경로가 포함되어 있습니다.
```
NDKDir=/Users/ovject/Library/Android/sdk/ndk/22.1.7171670
```
실행에 영향을 주지는 않으나 개발자 환경 정보 노출에 해당합니다. 릴리즈 빌드 시 제거를 권장합니다.

---

### 항목 2 — 불필요하거나 과도한 권한 설정

**결과: 양호**

선언된 권한 목록:

| 권한 | 용도 | 필요성 |
|---|---|---|
| INTERNET | 광고 로딩, 네트워크 통신 | 필요 |
| ACCESS_NETWORK_STATE | 네트워크 상태 확인 | 필요 |
| VIBRATE (x2 중복) | 진동 피드백 | 필요 (중복 선언은 무해하나 정리 권장) |
| WAKE_LOCK | 게임 플레이 중 화면 유지 | 필요 |
| RECEIVE_BOOT_COMPLETED | WorkManager 라이브러리 의존 | 라이브러리 요구사항 |

위치, 카메라, 연락처, SMS 등 민감 권한은 선언되지 않아 과도한 권한 문제는 없습니다.

---

### 항목 3 — 임의기능 등 악성행위 기능 존재

**결과: 양호**

`ServerSocket`, `Runtime->exec`, `ProcessBuilder` 패턴을 앱 고유 코드(`com/OVJECT/`, `com/yoyogames/`)에서 검색한 결과 미발견.

`AlarmManager`, `JobScheduler` 패턴은 `androidx.work` (WorkManager) 라이브러리 내에서만 발견되었으며, 이는 Google Play Services의 표준 백그라운드 작업 라이브러리입니다. 앱이 직접 사용하는 것이 아닌 광고 SDK 의존성입니다.

---

### 항목 4 — 정보 외부 유출

**결과: 양호**

앱 고유 코드(`com/OVJECT/`, `com/yoyogames/`)에서 `http://`, `https://`, 하드코딩 IP 주소 패턴을 검색한 결과 미발견.

외부 URL 패턴은 `com/google/android/gms/` (Google Ads SDK) 내에서만 발견되며, 이는 Google 광고 서버와의 표준 통신입니다. 허가되지 않은 외부 주소로의 정보 전송 코드는 없습니다.

---

### 항목 5 — 자원고갈

**결과: 점검 제외**

정적 분석으로 판단 불가. 런타임 점검(`/security-check 악어 이빨 runtime`) 실행 시 항목 20에서 배터리·트래픽 측정으로 점검합니다.

---

### 항목 6 — 루팅 및 탈옥 기기에서의 정상 동작

**결과: 취약**

`su`, `test-keys`, `RootBeer`, `SafetyNet`, `Build;->TAGS` 등 루팅 탐지 패턴을 앱 전체 smali에서 검색한 결과 미발견.

루팅 탐지 기능이 없어 루팅된 기기에서 게임 데이터 조작(점수 위변조, 인앱 결제 우회 등)이 가능합니다. 단, 앱이 순수 게임 앱으로 금융 정보나 개인 민감정보를 다루지 않아 실질적 위험도는 낮습니다.

**권고:** 루팅 탐지 라이브러리(예: RootBeer, SafetyNet Attestation API) 적용을 검토하세요.

---

### 항목 7 — ID 값의 변경

**결과: 양호**

`AndroidManifest.xml`에서 `android:process`, `android:permission` 속성을 확인한 결과, 기본 Activity(`RunnerActivity`)에 별도 프로세스나 커스텀 권한이 설정되지 않았습니다.

`SystemJobService`에 `android:permission="android.permission.BIND_JOB_SERVICE"`가 설정되어 있으나, 이는 Android 시스템 권한으로 표준적인 JobService 보호 방식입니다.

---

### 항목 8 — 동일키로 서명된 서로 다른 앱 간의 UID 공유

**결과: 양호**

`AndroidManifest.xml`에 `android:sharedUserId` 속성이 존재하지 않습니다.

---

### 항목 9 — 인텐트 권한의 올바른 설정

**결과: 양호**

컴포넌트별 exported 설정:

| 컴포넌트 | exported | 보호 |
|---|---|---|
| RunnerActivity | true (implicit — LAUNCHER) | MAIN/LAUNCHER intent-filter만 정의 |
| AdActivity | false | — |
| SystemJobService | true | BIND_JOB_SERVICE 시스템 권한 보호 |
| 기타 Service/Receiver | false | — |

`RunnerActivity`의 intent-filter는 `MAIN/LAUNCHER` 및 `LEANBACK_LAUNCHER`만 정의되어 과도한 필터링이 없습니다. `queries` 블록의 인텐트는 앱이 쿼리 가능한 외부 앱을 선언하는 것으로 노출 위험이 없습니다.

---

### 항목 10 — 인증 정보 생성 강도 적절성

**결과: 점검 제외**

`RunnerJNILib`에 `ShowLogin(username, password)` 다이얼로그 코드가 존재하나, 실제 구현체인 `RunnerSocial.Login()`이 빈 stub 메서드(`return-void`)로 확인되었습니다. GameMaker Studio 소셜 로그인 프레임워크의 미구현 기능입니다.

실제 서버 인증 기능이 없으므로 인증 강도 점검 대상에서 제외합니다.

---

### 항목 11 — 중요 정보의 평문 저장 및 전송

**결과: 주의**

**평문 전송:**
- `AndroidManifest.xml`에 `android:usesCleartextTraffic` 속성이 없고, `targetSdkVersion=30`이므로 기본적으로 HTTP 평문 통신이 차단됩니다. → 양호

**로그 출력:**
- `com/OVJECT/CrocoR/AdvertisingBase.smali`, `DemoGLSurfaceView.smali`에서 `android.util.Log.i()` 호출이 다수 발견되었습니다.
- 로그 내용은 광고 상태 및 GL 렌더링 이벤트로 확인되며 민감 정보 직접 출력은 발견되지 않았습니다.
- 단, 릴리즈 빌드에서 디버그 로그가 활성화된 상태입니다.

```
com/OVJECT/CrocoR/AdvertisingBase.smali
com/OVJECT/CrocoR/DemoGLSurfaceView.smali
com/yoyogames/runner/RunnerJNILib$22~24.smali
```

**권고:** 릴리즈 빌드에서는 `Log` 호출을 제거하거나 ProGuard/R8 규칙으로 제거해야 합니다.

---

### 항목 12 — 중요정보 저장 및 전송 시 취약한 암호 알고리즘 적용

**결과: 양호**

`Cipher`, `MessageDigest`, `DES`, `MD5`, `SHA-1`, `SecretKeySpec`, `KeyStore` 패턴이 `com/google/android/gms/` (Google Ads SDK) 내에서만 발견되었습니다.

앱 고유 코드(`com/OVJECT/`, `com/yoyogames/`)에서는 암호화 관련 코드가 사용되지 않았습니다. 앱이 직접 암호화를 적용하는 기능이 없으며, Google SDK의 내부 암호화는 Google의 보안 정책에 따라 관리됩니다.

---

### 항목 13 — 기타 중요정보의 평문 저장 및 전송

**결과: 주의**

**android_id 수집 확인:**
```smali
# com/yoyogames/runner/RunnerJNILib.smali
const-string v1, "android_id"
invoke-static {v0, v1}, Landroid/provider/Settings$Secure;->getString(...)
```

`Settings.Secure.ANDROID_ID`를 수집하는 코드가 확인됩니다. Android 기기 고유 식별자입니다.

**광고 식별자 수집:**
- `com/google/android/gms/ads/identifier/AdvertisingIdClient.smali` — Google 광고 식별자(GAID) 수집 (Google Play 정책에 따른 광고 SDK 표준 동작)

**IMEI/IMSI:** `TelephonyManager`, `Build.SERIAL` 수집 코드 미발견 → 양호

광고 기반 게임에서의 기기 식별자 수집은 일반적이나, 개인정보처리방침에 `android_id` 및 광고 식별자 수집 사실이 명시되어야 합니다.

**권고:** 개인정보처리방침에 기기 식별자 수집 및 이용 목적을 명시하세요.

---

### 항목 14 — 파일 다운로드 시 외부 주소 변조 및 파일 무결성 우회

**결과: 양호**

앱 고유 코드에서 `DownloadManager`, `PackageInstaller`, `AppUpdateManager` 직접 사용이 없습니다. `ContextCompat$LegacyServiceMapHolder.smali`에서 `DownloadManager` 참조가 있으나 이는 서비스 이름 상수 맵으로 실제 다운로드 기능이 아닙니다.

앱은 외부에서 파일을 다운로드하거나 패키지를 설치하는 기능이 없습니다.

---

### 항목 15 — 개인정보 및 개인위치 정보 수집 및 활용에 대한 동의

**결과: 양호**

Google UMP(User Messaging Platform) 기반 광고 동의 처리가 구현되어 있습니다.

- `assets/consentform.html` — 광고 동의 폼 HTML 파일
- `GooglePlayAdsExtension$11.smali` — `ConsentInfoUpdateListener` 구현 (광고 동의 상태 확인 및 처리)
- `GooglePlayAdsExtension$12.smali` — `ConsentForm.Builder`로 동의 폼 생성 및 표시
- `val$privacyPolicy` — 개인정보처리방침 URL 전달

위치 정보 수집(`LocationManager`) 코드 없음.

---

### 항목 16 — 난독화

**결과: 취약**

앱 고유 코드 전체에 난독화가 적용되지 않았습니다.

**증거 — `.source` 지시어 원본 유지:**
```
AdvertisingBase.smali     → .source "AdvertisingBase.java"
DemoGLSurfaceView.smali   → .source "DemoGLSurfaceView.java"
RunnerSocial.smali        → .source "RunnerSocial.java"
RunnerActivity.smali      → .source "RunnerActivity.java"
GooglePlayAdsExtension.smali → .source "GooglePlayAdsExtension.java"
```

**클래스/메서드명 원본 유지:**
- `AdvertisingBase`, `DemoGLSurfaceView`, `DemoRenderer`, `GooglePlayAdsExtension`, `GamepadHandler` 등 의미 있는 클래스명이 그대로 노출됩니다.
- 메서드명 `ShowLogin`, `Login`, `Logout`, `PostScore` 등 원본 그대로 노출됩니다.

단, Google Ads SDK 및 androidx 라이브러리는 `zzXXX` 형태의 난독화가 적용되어 있습니다.

**권고:** Android Studio의 R8/ProGuard를 적용하여 릴리즈 빌드 시 앱 고유 코드를 난독화하세요.
```groovy
// build.gradle
buildTypes {
    release {
        minifyEnabled true
        proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
    }
}
```

---

## 종합 의견

| 구분 | 건수 |
|---|---|
| 취약 | 2건 (항목 6, 16) |
| 주의 | 2건 (항목 11, 13) |
| 양호 | 10건 |
| 점검 제외 | 2건 (항목 5, 10) |

**Croco Roulette**는 GameMaker Studio 기반의 간단한 게임 앱으로, 전반적인 보안 수준은 양호한 편입니다. 발견된 취약점은 모두 위험도 낮음(Low)으로, 즉각적인 보안 위협보다는 보안 강화 권고 사항에 해당합니다.

### 우선 조치 권고

| 우선순위 | 항목 | 조치 사항 |
|---|---|---|
| 중간 | 항목 16 (난독화) | R8/ProGuard 적용으로 리버스 엔지니어링 방어 강화 |
| 중간 | 항목 6 (루팅 탐지) | RootBeer 등 루팅 탐지 라이브러리 적용 검토 |
| 낮음 | 항목 11 (로그) | 릴리즈 빌드의 Log.i() 호출 제거 |
| 낮음 | 항목 13 (기기정보) | 개인정보처리방침에 android_id 수집 명시 |
| 참고 | 항목 1 (빌드 정보) | options.ini의 NDK 절대 경로 제거 권장 |

### 런타임 추가 점검 권장

정적 분석에서 제외된 항목(자원고갈, 반복 설치, 삭제 안전성, 기능 정상동작)을 점검하려면:
```
/security-check 악어 이빨 runtime
```

---

*본 보고서는 APKTool 2.11.1을 이용한 정적 분석 결과입니다. 런타임 동작은 별도 점검이 필요합니다.*
