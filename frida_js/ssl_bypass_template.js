/**
 * SSL Pinning Bypass — 범용 템플릿
 *
 * 사용법:
 *   frida -U -f {패키지명} -l frida_js/ssl_bypass_template.js
 *
 * Burp Suite 프록시와 함께 사용:
 *   1. 기기 Wi-Fi 프록시를 Burp 주소로 설정
 *   2. Burp CA 인증서를 기기에 설치
 *   3. 이 스크립트로 SSL pinning 우회
 *   4. Burp에서 트래픽 캡처
 */

Java.perform(function () {
    console.log("[*] SSL Bypass Script Loaded");

    // === Hook 1: TrustManager Override ===
    try {
        var TrustManagerImpl = Java.use("com.android.org.conscrypt.TrustManagerImpl");
        TrustManagerImpl.verifyChain.overload(
            "[Ljava.security.cert.X509Certificate;",
            "java.lang.String",
            "java.net.Socket",
            "boolean",
            "[B"
        ).implementation = function (untrustedChain) {
            console.log("[+] TrustManagerImpl.verifyChain bypassed");
            return untrustedChain;
        };
    } catch (e) {
        console.log("[-] TrustManagerImpl not found: " + e.message);
    }

    // === Hook 2: X509TrustManager ===
    try {
        var X509TrustManager = Java.use("javax.net.ssl.X509TrustManager");
        var SSLContext = Java.use("javax.net.ssl.SSLContext");

        var TrustManager = Java.registerClass({
            name: "com.bypass.TrustManager",
            implements: [X509TrustManager],
            methods: {
                checkClientTrusted: function (chain, authType) {},
                checkServerTrusted: function (chain, authType) {},
                getAcceptedIssuers: function () {
                    return [];
                },
            },
        });

        var TrustManagers = [TrustManager.$new()];
        var sslContext = SSLContext.getInstance("TLS");
        sslContext.init(null, TrustManagers, null);
        console.log("[+] Custom TrustManager installed");
    } catch (e) {
        console.log("[-] X509TrustManager hook failed: " + e.message);
    }

    // === Hook 3: HostnameVerifier ===
    try {
        var HostnameVerifier = Java.use("javax.net.ssl.HostnameVerifier");
        var HttpsURLConnection = Java.use("javax.net.ssl.HttpsURLConnection");

        HttpsURLConnection.setDefaultHostnameVerifier.implementation = function (verifier) {
            console.log("[+] setDefaultHostnameVerifier bypassed");
        };
    } catch (e) {
        console.log("[-] HostnameVerifier hook failed: " + e.message);
    }

    // === Hook 4: WebViewClient SSL Error ===
    try {
        var WebViewClient = Java.use("android.webkit.WebViewClient");
        WebViewClient.onReceivedSslError.implementation = function (view, handler, error) {
            console.log("[+] WebViewClient SSL error bypassed");
            handler.proceed();
        };
    } catch (e) {
        console.log("[-] WebViewClient hook failed: " + e.message);
    }

    // === Hook 5: OkHttp CertificatePinner (v3) ===
    try {
        var CertificatePinner = Java.use("okhttp3.CertificatePinner");
        CertificatePinner.check.overload("java.lang.String", "java.util.List").implementation = function (hostname, peerCertificates) {
            console.log("[+] OkHttp3 CertificatePinner bypassed for: " + hostname);
        };
    } catch (e) {
        console.log("[-] OkHttp3 CertificatePinner not found: " + e.message);
    }

    console.log("[*] SSL Bypass hooks installed. Ready for traffic capture.");
});
