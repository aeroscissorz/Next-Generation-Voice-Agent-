# Implementation Plan: Voice UX Fixes

## Overview

Two targeted fixes to the Interceptor service: tuning VAD parameters for easier interruption, and adding length/format validation to the user ID pipeline. All changes are in Python within the Interceptor directory.

## Tasks

- [x] 1. Update VAD configuration for improved responsiveness
  - [x] 1.1 Update turn_detection parameters in `Interceptor/main.py`
    - Change `threshold` from `0.75` to `0.55`
    - Change `silence_duration_ms` from `700` to `400`
    - Change `prefix_padding_ms` from `250` to `200`
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. Add user ID length validation and logging to extraction
  - [x] 2.1 Define validation constants and update `extract_user_id_from_spoken()` in `Interceptor/utils/helpers.py`
    - Add `USER_ID_MIN_LENGTH = 2` and `USER_ID_MAX_LENGTH = 10` constants
    - After stripping non-digit characters, check length is within [2, 10]; return empty string if not
    - Add INFO-level logging for raw input, normalized output, and rejection reason
    - _Requirements: 2.1, 2.2, 4.1, 4.2_

  - [ ]* 2.2 Write property tests for `extract_user_id_from_spoken()`
    - **Property 1: Extraction produces digits only**
    - **Validates: Requirements 2.1**
    - **Property 2: Extraction enforces length bounds**
    - **Validates: Requirements 2.2**
    - **Property 7: Extraction logs raw input, output, and rejection reason**
    - **Validates: Requirements 4.1, 4.2**

- [x] 3. Add length validation and logging to `validate_user_id()`
  - [x] 3.1 Update `validate_user_id()` in `Interceptor/services/voice_auth.py`
    - Import `USER_ID_MIN_LENGTH` and `USER_ID_MAX_LENGTH` from `utils.helpers`
    - Add length check before the DB query: reject IDs outside [2, 10] digits with descriptive message
    - Add INFO-level logging for received ID, length, and validation outcome
    - _Requirements: 2.3, 2.4, 2.5, 4.3, 4.4_

  - [ ]* 3.2 Write property tests for `validate_user_id()`
    - **Property 3: Validation rejects invalid-length IDs with proper response**
    - **Validates: Requirements 2.3, 2.4**
    - **Property 4: Validation returns proper success tuple**
    - **Validates: Requirements 2.5**
    - **Property 8: Validation logs ID, length, and outcome**
    - **Validates: Requirements 4.3, 4.4**

- [x] 4. Ensure consistent tool call response structure
  - [x] 4.1 Update `_handle_validate_user()` in `Interceptor/main.py`
    - Ensure failed validation responses include both `reason` and `message` fields
    - Ensure success responses include `authenticated`, `customer_id`, and `message` fields
    - _Requirements: 3.1, 3.2, 3.3_

  - [ ]* 4.2 Write property tests for `_handle_validate_user()` response structure
    - **Property 5: Handler returns proper failure JSON structure**
    - **Validates: Requirements 3.2**
    - **Property 6: Handler returns proper success JSON structure**
    - **Validates: Requirements 3.3**

- [x] 5. Final checkpoint
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- All changes are within the `Interceptor/` directory — no frontend or backend changes needed
- Property tests use the `hypothesis` library for Python
- VAD tuning (task 1) is independent of validation fixes (tasks 2–4) and can be deployed separately
