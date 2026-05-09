# Quy tắc tính công — Tài liệu tra cứu

> Nguồn sự thật: `reports/calculator.py`  
> Cập nhật lần cuối: 2026-05-09

---

## 1. Các loại lỗi chấm công (error_types)

| Mã lỗi | Tên | Phía | Có `minutes`? |
|--------|-----|------|---------------|
| `LATE` | Đi muộn | CI | ✅ `minutes_late` |
| `MISSING_IN` | Thiếu giờ vào | CI | ❌ |
| `EARLY_LEAVE` | Về sớm | CO | ✅ `minutes_early` |
| `MISSING_OUT` | Thiếu giờ ra | CO | ❌ |
| `ABSENT` | Vắng mặt cả ngày | CI + CO | ❌ |

---

## 2. Lý do giải trình và result code

Mỗi bản ghi lỗi có 1 `ci_reason` + 1 `co_reason`. Result code (`RC`) được tính độc lập cho CI và CO bởi `_ci_result()` / `_co_result()`:

### 2.1 Không có lỗi phía đó → `RC.OK` (không điều chỉnh)

### 2.2 Chưa giải trình hoặc bị từ chối

RC phụ thuộc vào **loại lỗi**, không phụ thuộc lý do:

| Loại lỗi | RC | Ý nghĩa |
|----------|----|---------|
| `LATE` hoặc `EARLY_LEAVE` | `UNEXCUSED` | Có timestamp → trừ đúng số phút |
| `MISSING_IN` hoặc `MISSING_OUT` | `UNEXCUSED_BLOCK` | Không biết giờ đến/về → trừ cả nửa ngày |

### 2.3 Được duyệt — tra theo lý do giải trình

| Lý do giải trình | RC | Hiệu ứng |
|------------------|----|---------|
| Đi muộn/ Về sớm | `LEAVE` | Số phút muộn/sớm chuyển sang giờ phép |
| Quên chấm công | `OK` | Bỏ qua lỗi, tính full công |
| Trị liệu tại nhà | `OK` | Bỏ qua lỗi, tính full công |
| Đi công tác / sự kiện / công việc khác | `OK` | Bỏ qua lỗi, tính full công |
| Nghỉ phép nửa ngày | `LEAVE_BLOCK` | Trừ cả block nửa ngày vào phép |
| Nghỉ phép cả ngày | `DAY_OFF` | Xử lý đặc biệt → xem §4 |
| Nghỉ không lương | `DAY_OFF` | Xử lý đặc biệt → xem §4 |

---

## 3. Tính giờ điều chỉnh (Δwork, Δleave)

### 3.1 Định nghĩa block ca

```
morning_block  = check_in → break_start      (ví dụ Ca 8-17: 08:00–12:00 = 4h)
afternoon_block = break_end → check_out       (ví dụ Ca 8-17: 13:00–17:00 = 4h)
break_duration  = break_start → break_end     (ví dụ: 12:00–13:00 = 60p)
```

### 3.2 Bảng điều chỉnh theo result code

| RC | Tiếng Việt | Δwork | Δleave | Ghi chú |
|----|------------|-------|--------|---------|
| `OK` | Công | 0 | 0 | Không lỗi / đã tha — full công |
| `DAY_OFF` | Nghỉ | 0 | 0 | Nghỉ cả phiên — xử lý ở §4 |
| `LEAVE` | Phép (phút) | −effective_min/60 | +effective_min/60 | Phút muộn/sớm tính vào phép (xem §3.3) |
| `UNEXCUSED` | Không (trừ phút) | −effective_min/60 | 0 | Phút muộn/sớm trừ unpaid (xem §3.3) |
| `LEAVE_BLOCK` | Phép (nửa ngày) | −block | +block | Nghỉ nửa ngày — block trừ vào phép |
| `UNEXCUSED_BLOCK` | Không (trừ block) | −block | 0 | Chưa duyệt — block trừ unpaid |

### 3.3 Quy tắc bỏ giờ nghỉ trưa (effective_minutes)

Áp dụng cho `LEAVE` và `UNEXCUSED` khi số phút muộn/sớm **vượt qua ranh giới block**:

```
effective_minutes = minutes - min(break_duration, max(0, minutes - block_min))
```

**Ví dụ Ca 8-17 (morning_block=240p, break=60p):**

| minutes_late | Giải thích | effective |
|-------------|-----------|-----------|
| 5p | Vào lúc 08:05, chưa qua break | 5p |
| 281p | Vào lúc 12:41, đang trong break (qua sáng 41p) | 281 − 41 = 240p |
| 341p | Vào lúc 13:41, qua cả break (tràn 41p sang chiều) | 341 − 60 = 281p |

### 3.4 LEAVE_BLOCK overflow (nghỉ nửa ngày + tràn ca)

Khi `minutes` > `block + break` (tràn sang ca bên kia):

```
overflow = minutes - block_min - break_min   (nếu > 0)
work  -= overflow / 60
leave += overflow / 60    # tràn tính phép (LCI/ECO approved)
```

**Ví dụ Ca 8-17:**

| Ngày | minutes | block | break | overflow | ΔW | ΔL |
|------|---------|-------|-------|----------|----|-----|
| LATE 281p (`LEAVE_BLOCK`) | 281 | 240p | 60p | max(0, 281−300)=0 | −4h | +4h |
| LATE 341p (`LEAVE_BLOCK`) | 341 | 240p | 60p | 341−300=41p | −4h−0.68h | +4h+0.68h |
| EARLY 307p (`LEAVE_BLOCK`) | 307 | 240p | 60p | 307−300=7p | −4h−0.12h | +4h+0.12h |

> **Khi rejected (`UNEXCUSED`):** overflow cũng được bỏ qua break nhờ `effective_minutes`, nhưng toàn bộ là unpaid (L=0).

---

## 4. Trường hợp đặc biệt: ABSENT

`ABSENT` = vắng mặt cả ngày (không có CI lẫn CO). Xử lý riêng trước khi vào logic CI/CO:

| Lý do | Phê duyệt | W | L |
|-------|-----------|---|---|
| **Nghỉ phép cả ngày** | ✅ | 0 | base_work (8h) |
| **Nghỉ không lương** | ✅ | 0 | 0 |
| Bất kỳ lý do nào | ❌ Từ chối | 0 | 0 |
| Không giải trình | — | 0 | 0 |

---

## 5. QCC lần 3+ (Quên chấm công tích lũy)

- Đếm QCC **approved** theo tháng, theo nhân viên, theo thứ tự ngày.
- Từ **lần 3 trở đi**: sau khi tính xong W/L của ngày đó → split 50/50:

```python
if is_qcc_record(exp) and qcc_count >= 3:
    half = round(work / 2, 2)
    leave += half
    work = half
```

| Lần QCC | Hiệu ứng |
|---------|----------|
| 1, 2 | Full công, không trừ (`RC.OK`) |
| 3+ | Giờ công còn lại / 2 → phép |

---

## 6. Luồng tính hoàn chỉnh cho 1 bản ghi

```
record.error_types:
  └─ [] (OK)              → (base_work, base_leave) — xong
  └─ [ABSENT]             → §4 — xong
  └─ [LATE/MISSING_IN/EARLY_LEAVE/MISSING_OUT]
       ├─ result_ci = _ci_result(error_set, ci_reason, ci_approved)
       ├─ result_co = _co_result(error_set, co_reason, co_approved)
       ├─ (nếu result_ci==DAY_OFF AND result_co==DAY_OFF) → §4 — xong
       ├─ δW_ci, δL_ci = _apply_adj(result_ci, minutes_late, shift, 'morning')   [§3.2, §3.3]
       ├─ δW_co, δL_co = _apply_adj(result_co, minutes_early, shift, 'afternoon') [§3.2, §3.3]
       ├─ work = base_work + δW_ci + δW_co
       ├─ leave = base_leave + δL_ci + δL_co
       ├─ (LEAVE_BLOCK overflow nếu có) → §3.4
       ├─ work = max(work, 0)
       └─ (QCC lần 3+) → §5
```

---

## 7. Điều kiện chạy tính công

Trước khi `calculate_month` chạy, hệ thống kiểm tra:
- Mọi bản ghi `status='error'` phải có đủ `ci_reason` (nếu có CI issue) và `co_reason` (nếu có CO issue).
- Nếu còn thiếu → `ValueError`, không cho tính.

---

## 8. Các test case tham chiếu

File: `reports/tests/test_calculator.py`

| Test | Mô tả |
|------|-------|
| `test_ok_record_full_hours` | OK → 8h/0h |
| `test_late_approved_phep` | LATE 30p, "Đi muộn" approved → 7.5h/0.5h |
| `test_late_unpaid` | LATE 30p, không giải trình → 7.5h/0h |
| `test_missing_in_no_explanation_block_unpaid` | MISSING_IN, không giải trình → 4h/0h |
| `test_missing_in_phep2` | MISSING_IN, "Nghỉ nửa ngày" approved → 4h/4h |
| `test_missing_in_approved_cong` | MISSING_IN, QCC approved → 8h/0h |
| `test_early_leave_unpaid` | EARLY_LEAVE 45p, không giải trình → 7.25h/0h |
| `test_missing_out_phep2` | MISSING_OUT, "Nghỉ nửa ngày" approved → 4.5h/3.5h |
| `test_late_phep2_with_overflow` | LATE 341p (tràn 11p sau break 90p) → W=8−4−11/60, L=4+11/60 |
| `test_early_phep2_with_overflow` | EARLY 307p (tràn 7p sau break 90p) → W=8−3.5−7/60, L=3.5+7/60 |
| `test_absent_approved_nghi_phep` | ABSENT, "Nghỉ phép cả ngày" approved → 0h/8h |
| `test_absent_no_explanation` | ABSENT, không giải trình → 0h/0h |
| `test_absent_unpaid` | ABSENT, "Nghỉ không lương" → 0h/0h |
| `test_qcc_lần_1_no_split` | QCC lần 1 → 8h/0h |
| `test_qcc_lần_3_split_50_50` | QCC lần 3 → 4h/4h |
| `test_calculate_all_ok_days` | Integration: 5 ngày OK → 40h/0h |
| `test_calculate_blocks_incomplete_explanations` | Integration: block nếu còn thiếu giải trình |
| `test_calculate_late_with_approved_phep` | Integration: LATE 30p approved → 7.5h/0.5h |
| `test_calculate_absent_with_leave` | Integration: ABSENT phép → 0h/8h |
