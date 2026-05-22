# BUG-18453 수동 검증 가이드 (테스터용)

- 단말: AT-M150 (ZEM 포켓몬3) / 빌드 Z0518U_GMS_817 / SIM LGU+
- DebugScreen 열기: 단말 히든코드(아는 경우) 또는 PC에서 1회
  `adb -s f2bfcc3c shell am start -n com.android.phone/.settings.DebugScreen`
  - 화면 잠겨 빈 화면이면 단말 깨우고 잠금해제 후 다시 실행
  - 화면 자동 갱신 안 됨 → 값 다시 보려면 DebugScreen 재진입(뒤로 → 다시 열기)
- 보는 필드: **IP:** / **IMS IP:** / **DUN IP:**

## 검증 4항목 (단말에서 직접)

### 1. bootup 시 internet IP / IMS IP 표시
1. 모바일 데이터 **ON** 확인 (콜드부팅 직후 OFF일 수 있음 — 켜고 데이터 잡힐 때까지 대기)
2. DebugScreen 진입
3. 확인: **IP:** 에 internet IP(10.x), **IMS IP:** 에 IPv6 표시 → 표시되면 정상
- 참고: 데이터 OFF면 IP 안 나옴(정상). 데이터 잡힌 뒤 판단할 것

### 2. tethering 시 tethering IP 표시 (WIFI / USB 각각)
1. 모바일 핫스팟(WIFI) **ON** → (필요시 다른 기기 1대 연결)
2. DebugScreen 진입 → **DUN IP:** 에 tethering IP(10.x) 표시되는지
3. USB 테더링도 동일 반복 (USB 케이블 PC 연결 상태에서 USB 테더링 ON)
- 확인 포인트: DUN IP 값이 채워지면 "표시" 정상. (자동검증 결과: WIFI/USB 모두 표시됨)

### 3. "DUN" 문구 미표시
1. tethering 활성/비활성 모두에서 DebugScreen 확인
2. 화면에 **"DUN"** 글자(라벨 `DUN IP:`)가 보이는지
- 확인 포인트: 자동검증에서는 **"DUN IP:" 라벨이 항상 표시됨** (지시 #3 "미표시"와 상충). 직접 눈으로 재확인 요망

### 4. tethering 해제 시 tethering IP 미표시  ★핵심★
1. **WIFI 핫스팟 OFF** → 잠시 후 DebugScreen 재진입 → **DUN IP:** 값이 사라졌는지
2. **USB 테더링 OFF** → 잠시 후 DebugScreen 재진입 → **DUN IP:** 값이 사라졌는지
- 확인 포인트 (자동검증 결과, 직접 재현 확인 바람):
  - **WIFI 해제: DUN IP 값이 안 사라지고 직전 IP가 그대로 남음 (이상)**
  - **USB 해제: DUN IP 값이 정상적으로 사라짐 (정상)**
  - 같은 단말에서 WIFI/USB 해제 동작이 다름 → 이 비대칭을 직접 재현 확인이 목적

## 관찰 기록 양식 (한 줄씩)

```
[항목] [방식 WIFI/USB] [동작 ON/OFF] DUN IP 화면값= ____  / 기대= ____  / 판정 PASS|FAIL
```

## 모니터링 (PC, Claude)

테스터가 단말에서 토글하는 동안 Claude가 ground-truth(DUN PDN 연결/IP, tethering upstream)를 실시간 출력.
화면값(테스터)과 PDN상태(모니터)를 같은 시각으로 대조 → stale 여부 객관 판정.
