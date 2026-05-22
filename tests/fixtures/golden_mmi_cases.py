"""Golden MMI case fixture.

패턴별 분포: 메뉴 체인 6, 토글 5, verify 4, key 3, input 2 = 20건
추가: MANUAL_REQUIRED 2건, AMBIGUOUS_NL 1건 = 총 23건

각 케이스는 실제 MMI 엑셀 시트에서 추출한 대표 절차를 기반으로 한다.
"""

GOLDEN_CASES = [
    # =========================================================
    # 메뉴 체인 (6건)
    # =========================================================
    {
        "id": "menu_01",
        "pattern": "메뉴 체인",
        "procedure": "설정 > 안심 기능 > 수신 차단 > 수신차단 전화번호 추가",
        "expected": "'전화와 문자 메시지를 차단할 번호' 팝업 발생",
        "expected_classification": "SEMI_AUTO",
        "expected_intent_types": ["navigate", "navigate", "navigate", "navigate"],
        "expected_steps": [
            {"action": "tap_text", "text": "설정"},
            {"action": "tap_text", "text": "안심 기능"},
            {"action": "tap_text", "text": "수신 차단"},
            {"action": "tap_text", "text": "수신차단 전화번호 추가"},
        ],
    },
    {
        "id": "menu_02",
        "pattern": "메뉴 체인 (깊은 탐색)",
        "procedure": "설정 > 네트워크 및 인터넷 > 인터넷 > 통신사 설정 > 기본 네트워크 유형",
        "expected": "기본 네트워크 유형 메뉴로 진입된다",
        "expected_classification": "SEMI_AUTO",
        "expected_intent_types": ["navigate", "navigate", "navigate", "navigate", "navigate"],
        "expected_steps": [
            {"action": "tap_text", "text": "설정"},
            {"action": "tap_text", "text": "네트워크 및 인터넷"},
            {"action": "tap_text", "text": "인터넷"},
            {"action": "tap_text", "text": "통신사 설정"},
            {"action": "tap_text", "text": "기본 네트워크 유형"},
        ],
    },
    {
        "id": "menu_03",
        "pattern": "메뉴 체인 (퀵세팅)",
        "procedure": "퀵 셋팅 > 모바일 데이터 아이콘 탭",
        "expected": "모바일 데이터가 켜진다",
        "expected_classification": "SEMI_AUTO",
        "expected_intent_types": ["navigate", "navigate"],
        "expected_steps": [
            {"action": "tap_text", "text": "퀵 셋팅"},
            {"action": "tap_text", "text": "모바일 데이터 아이콘 탭"},
        ],
    },
    {
        "id": "menu_04",
        "pattern": "메뉴 체인 (설정 > 디스플레이)",
        "procedure": "설정 > 디스플레이 > 화면 자동 회전",
        "expected": "화면 자동 회전 메뉴 진입된다",
        "expected_classification": "SEMI_AUTO",
        "expected_intent_types": ["navigate", "navigate", "navigate"],
        "expected_steps": [
            {"action": "tap_text", "text": "설정"},
            {"action": "tap_text", "text": "디스플레이"},
            {"action": "tap_text", "text": "화면 자동 회전"},
        ],
    },
    {
        "id": "menu_05",
        "pattern": "메뉴 체인 (연락처)",
        "procedure": "연락처 > 화면 우하단의 [+] Tap > 휴대전화 선택",
        "expected": "연락처 추가 화면이 표시된다",
        "expected_classification": "SEMI_AUTO",
        "expected_intent_types": ["navigate", "navigate", "navigate"],
        "expected_steps": [
            {"action": "tap_text", "text": "연락처"},
            {"action": "tap_text", "text": "화면 우하단의 [+] Tap"},
            {"action": "tap_text", "text": "휴대전화 선택"},
        ],
    },
    {
        "id": "menu_06",
        "pattern": "메뉴 체인 (삭제 절차)",
        "procedure": "설정 > 안심 기능 > 수신 차단 > 등록된 수신차단 전화번호 삭제",
        "expected": "해당 번호를 차단 해제 하겠냐는 팝업 노출",
        "expected_classification": "SEMI_AUTO",
        "expected_intent_types": ["navigate", "navigate", "navigate", "navigate"],
        "expected_steps": [
            {"action": "tap_text", "text": "설정"},
            {"action": "tap_text", "text": "안심 기능"},
            {"action": "tap_text", "text": "수신 차단"},
            {"action": "tap_text", "text": "등록된 수신차단 전화번호 삭제"},
        ],
    },

    # =========================================================
    # 토글 (5건)
    # =========================================================
    {
        "id": "toggle_01",
        "pattern": "토글 (Wi-Fi OFF)",
        "procedure": "퀵 셋팅 > Wi-Fi 아이콘 Long 탭 > Wi-Fi 토글 버튼 OFF",
        "expected": "Wi-Fi OFF되고 아이콘 백그라운드 컬러가 Empty 된다.",
        "expected_classification": "SEMI_AUTO",
        "expected_intent_types": ["navigate", "navigate", "toggle"],
        "expected_steps": [
            {"action": "tap_text", "text": "퀵 셋팅"},
            {"action": "tap_text", "text": "Wi-Fi 아이콘 Long 탭"},
            # toggle은 현재 미구현 → warning만 남김, step 없음
        ],
        "expected_warnings_contain": ["토글 intent"],
    },
    {
        "id": "toggle_02",
        "pattern": "토글 (모바일 데이터 On)",
        "procedure": "설정 > 네트워크 및 인터넷 > 모바일 네트워크 > 모바일 데이터 On",
        "expected": "모바일 데이터를 켭니다 팝업 발생",
        "expected_classification": "SEMI_AUTO",
        "expected_intent_types": ["navigate", "navigate", "navigate", "toggle"],
        "expected_steps": [
            {"action": "tap_text", "text": "설정"},
            {"action": "tap_text", "text": "네트워크 및 인터넷"},
            {"action": "tap_text", "text": "모바일 네트워크"},
            # toggle On → warning
        ],
        "expected_warnings_contain": ["토글 intent"],
    },
    {
        "id": "toggle_03",
        "pattern": "토글 (어두운 테마 On/Off)",
        "procedure": "홈화면 길게 누르기 > 배경화면 및 스타일 > 어두운 테마 On",
        "expected": "어두운 테마가 적용됨",
        "expected_classification": "SEMI_AUTO",
        "expected_intent_types": ["navigate", "navigate", "toggle"],
        "expected_steps": [
            {"action": "tap_text", "text": "홈화면 길게 누르기"},
            {"action": "tap_text", "text": "배경화면 및 스타일"},
        ],
        "expected_warnings_contain": ["토글 intent"],
    },
    {
        "id": "toggle_04",
        "pattern": "토글 (비행기 모드)",
        "procedure": "퀵 셋팅 > 비행기 모드 탭",
        "expected": "비행기 모드가 켜진다",
        "expected_classification": "SEMI_AUTO",
        "expected_intent_types": ["navigate", "navigate"],
        "expected_steps": [
            {"action": "tap_text", "text": "퀵 셋팅"},
            {"action": "tap_text", "text": "비행기 모드 탭"},
        ],
    },
    {
        "id": "toggle_05",
        "pattern": "토글 (화면 자동 회전 활성화)",
        "procedure": "퀵 셋팅 > 자동 회전 아이콘 탭 > 활성화",
        "expected": "화면 자동 회전이 활성화된다",
        "expected_classification": "SEMI_AUTO",
        "expected_intent_types": ["navigate", "navigate", "toggle"],
        "expected_steps": [
            {"action": "tap_text", "text": "퀵 셋팅"},
            {"action": "tap_text", "text": "자동 회전 아이콘 탭"},
        ],
        "expected_warnings_contain": ["토글 intent"],
    },

    # =========================================================
    # verify (4건)
    # =========================================================
    {
        "id": "verify_01",
        "pattern": "verify (HD 표시 확인)",
        "procedure": "인디게이터 확인",
        "expected": "인디케이터에 HD 보이스 이미지가 표시된다.",
        "expected_classification": "SEMI_AUTO",
        "expected_intent_types": ["verify_text"],
        "expected_steps": [],  # "인디게이터 확인" → verify_text로 파싱되나 실질적으로 모호
    },
    {
        "id": "verify_02",
        "pattern": "verify (잠금화면 노출)",
        "procedure": "Lockscreen 확인",
        "expected": "상단 인디케이터 영역 상태 정보 노출된다",
        "expected_classification": "SEMI_AUTO",
        "expected_intent_types": ["verify_text"],
        "expected_steps": [],
    },
    {
        "id": "verify_03",
        "pattern": "verify (메뉴 진입 확인)",
        "procedure": "설정 > 디스플레이 > 잠금 화면",
        "expected": "잠금 화면 설정 메뉴로 진입된다",
        "expected_classification": "SEMI_AUTO",
        "expected_intent_types": ["navigate", "navigate", "navigate"],
        "expected_steps": [
            {"action": "tap_text", "text": "설정"},
            {"action": "tap_text", "text": "디스플레이"},
            {"action": "tap_text", "text": "잠금 화면"},
        ],
    },
    {
        "id": "verify_04",
        "pattern": "verify (다이얼러 전환)",
        "procedure": "Lockscreen 확인 후 통화 아이콘 위로 Drag 한다",
        "expected": "다이얼러 화면으로 전환된다",
        "expected_classification": "SEMI_AUTO",
        "expected_intent_types": ["verify_text"],
        "expected_steps": [],
    },

    # =========================================================
    # key (3건)
    # =========================================================
    {
        "id": "key_01",
        "pattern": "key (HOME)",
        "procedure": "Home 키 입력",
        "expected": "홈화면으로 전환된다",
        "expected_classification": "SEMI_AUTO",
        "expected_intent_types": ["press_key"],
        "expected_steps": [
            {"action": "key", "keycode": "HOME"},
        ],
    },
    {
        "id": "key_02",
        "pattern": "key (BACK)",
        "procedure": "Back 키 입력",
        "expected": "이전 화면으로 돌아간다",
        "expected_classification": "SEMI_AUTO",
        "expected_intent_types": ["press_key"],
        "expected_steps": [
            {"action": "key", "keycode": "BACK"},
        ],
    },
    {
        "id": "key_03",
        "pattern": "key (최근앱)",
        "procedure": "최근앱 키 입력",
        "expected": "최근 앱 목록이 표시된다",
        "expected_classification": "SEMI_AUTO",
        "expected_intent_types": ["press_key"],
        "expected_steps": [
            {"action": "key", "keycode": "APP_SWITCH"},
        ],
    },

    # =========================================================
    # input (2건)
    # =========================================================
    {
        "id": "input_01",
        "pattern": "input (번호 입력)",
        "procedure": "설정 > 안심 기능 > 수신 차단 > 전화 번호 입력 필드 탭 > 번호 입력",
        "expected": "번호가 입력되고 차단 버튼이 활성화됨",
        "expected_classification": "SEMI_AUTO",
        "expected_intent_types": ["navigate", "navigate", "navigate", "navigate", "input_text"],
        "expected_steps": [
            {"action": "tap_text", "text": "설정"},
            {"action": "tap_text", "text": "안심 기능"},
            {"action": "tap_text", "text": "수신 차단"},
            {"action": "tap_text", "text": "전화 번호"},
            # input_text → 실제 값 없으므로 warning만
        ],
        "expected_warnings_contain": ["입력 대상"],
    },
    {
        "id": "input_02",
        "pattern": "input (검색어 입력)",
        "procedure": "연락처 > 검색 아이콘 탭 > 임의 문자열 입력",
        "expected": "검색 결과가 표시된다",
        "expected_classification": "SEMI_AUTO",
        "expected_intent_types": ["navigate", "navigate", "input_text"],
        "expected_steps": [
            {"action": "tap_text", "text": "연락처"},
            {"action": "tap_text", "text": "검색 아이콘 탭"},
        ],
        "expected_warnings_contain": ["입력 대상"],
    },

    # =========================================================
    # MANUAL_REQUIRED (2건)
    # =========================================================
    {
        "id": "manual_01",
        "pattern": "MANUAL (이어폰)",
        "procedure": "유선 이어폰 연결 후 통화 확인",
        "expected": "이어폰으로 음성 출력",
        "expected_classification": "MANUAL_REQUIRED",
        "expected_intent_types": [],
        "expected_steps": [],
    },
    {
        "id": "manual_02",
        "pattern": "MANUAL (외부 단말)",
        "procedure": "발신 단말에서 DUT로 전화 발신",
        "expected": "수신 화면 표시",
        "expected_classification": "MANUAL_REQUIRED",
        "expected_intent_types": [],
        "expected_steps": [],
    },

    # =========================================================
    # AMBIGUOUS_NL (1건)
    # =========================================================
    {
        "id": "ambiguous_01",
        "pattern": "AMBIGUOUS (모호한 절차)",
        "procedure": "정상 동작 확인한다",
        "expected": "문제 없는지 확인",
        "expected_classification": "AMBIGUOUS_NL",
        "expected_intent_types": [],
        "expected_steps": [],
    },
]
