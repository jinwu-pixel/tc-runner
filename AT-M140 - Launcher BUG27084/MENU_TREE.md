# BUG27084 UI 경로 원장

좌표는 profile이 소유하며 이 문서는 의미 경로만 기록한다. 화면 라벨·role·package가 맞지 않으면 진행하지 않는다.

## 위젯 배치

```text
일반모드 HOME
└─ 빈 영역 길게 누르기
   └─ 위젯
      └─ 검색
         ├─ SimpleClock
         │  └─ provider preview → drag-and-drop → 설정 OK
         └─ AccuWeather
            └─ 36시간 예보 → drag-and-drop → 설정 저장
```

## HOME mode 전환

```text
설정
└─ 홈 화면 설정
   └─ 홈 화면 모드
      ├─ 일반모드 → 적용
      └─ 간편모드 → 적용
```

- 안전 시작·종료 role: 간편모드 `com.hnlens.simplemode`
- trigger role: 일반모드 `com.hnlens.launcher3`
- stale arm 중 일반모드 복귀는 BUG27084 crash를 유발할 수 있으므로 harness의 exact phase gate 밖에서 수행하지 않는다.

## 정상 복구 확인

간편모드 전환 뒤 HOME role holder, resumed activity, UI hierarchy package가 모두 `com.hnlens.simplemode`일 때만 `RESTORED_SAFE`로 판정한다. 화면 외형만으로 복구를 선언하지 않는다.
