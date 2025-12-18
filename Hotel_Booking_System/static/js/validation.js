// static/validation.js

document.addEventListener("DOMContentLoaded", function() {
    // 1. 選取 DOM 元素
    const checkInInput = document.querySelector('input[name="check_in_date"]');
    const checkOutInput = document.querySelector('input[name="check_out_date"]');
    const form = document.querySelector('form');

    // 確保這些元素存在才執行，避免在沒有表單的頁面報錯
    if (form && checkInInput && checkOutInput) {
        
        // 2. 監聽表單送出事件 (Submit Validation)
        form.addEventListener('submit', function(event) {
            const checkInDate = new Date(checkInInput.value);
            const checkOutDate = new Date(checkOutInput.value);

            // 驗證邏輯：確保退房日期晚於入住日期
            if (checkOutDate <= checkInDate) {
                event.preventDefault(); // 阻止表單送出
                alert("Error: Check-out date must be later than check-in date!"); // 顯示錯誤訊息
                checkOutInput.focus(); // 將游標移回錯誤欄位
            }
        });

        // 3. (優化體驗) 當改變入住日期時，自動限制退房日期的最小值
        checkInInput.addEventListener('change', function() {
            checkOutInput.min = checkInInput.value;
        });
    }
});