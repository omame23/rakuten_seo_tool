// メインJavaScript

$(document).ready(function() {
    // アラートの自動消去（alert-info は除外）
    setTimeout(function() {
        $('.alert:not(.alert-info)').fadeOut('slow');
    }, 5000);
    
    // ツールチップの初期化
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });
    
    // フォームバリデーション
    $('.needs-validation').on('submit', function(event) {
        var form = this;
        if (!form.checkValidity()) {
            event.preventDefault();
            event.stopPropagation();
        } else {
            // ローディング表示
            var submitBtn = $(form).find('#submit-btn');
            if (submitBtn.length) {
                submitBtn.prop('disabled', true);
                submitBtn.find('.spinner-border').removeClass('d-none');
                submitBtn.find('i').addClass('d-none');
            }
        }
        $(form).addClass('was-validated');
    });
    
    // パスワード表示/非表示トグル
    $('.password-toggle').on('click', function(e) {
        e.preventDefault();
        var passwordField = $(this).siblings('input');
        var type = passwordField.attr('type') === 'password' ? 'text' : 'password';
        passwordField.attr('type', type);
        $(this).find('i').toggleClass('fa-eye fa-eye-slash');
    });
    
    // パスワード強度チェック
    $('#id_password1').on('input', function() {
        var password = $(this).val();
        var strength = checkPasswordStrength(password);
        var strengthBar = $('#password-strength');
        
        if (strengthBar.length === 0) {
            $(this).after('<div id="password-strength" class="progress mt-2" style="height: 5px;"><div class="progress-bar"></div></div>');
            strengthBar = $('#password-strength');
        }
        
        var progressBar = strengthBar.find('.progress-bar');
        progressBar.removeClass('bg-danger bg-warning bg-success');
        
        if (password.length === 0) {
            progressBar.css('width', '0%');
            return;
        }
        
        if (strength < 30) {
            progressBar.addClass('bg-danger').css('width', '25%');
        } else if (strength < 60) {
            progressBar.addClass('bg-warning').css('width', '50%');
        } else if (strength < 80) {
            progressBar.addClass('bg-warning').css('width', '75%');
        } else {
            progressBar.addClass('bg-success').css('width', '100%');
        }
    });
    
    // パスワード確認チェック
    $('#id_password2').on('input', function() {
        var password1 = $('#id_password1').val();
        var password2 = $(this).val();
        
        if (password2.length > 0) {
            if (password1 === password2) {
                $(this).removeClass('is-invalid').addClass('is-valid');
            } else {
                $(this).removeClass('is-valid').addClass('is-invalid');
            }
        } else {
            $(this).removeClass('is-valid is-invalid');
        }
    });
    
    // 確認ダイアログ
    $('.confirm-action').on('click', function(e) {
        var message = $(this).data('confirm-message') || '本当に実行しますか？';
        if (!confirm(message)) {
            e.preventDefault();
        }
    });
    
    // スムーススクロール
    $('a[href^="#"]').on('click', function(event) {
        var target = $(this.getAttribute('href'));
        if (target.length) {
            event.preventDefault();
            $('html, body').stop().animate({
                scrollTop: target.offset().top - 80
            }, 800);
        }
    });
});

// ローディング表示
function showLoading() {
    $('#loading-overlay').show();
}

function hideLoading() {
    $('#loading-overlay').hide();
}

// Ajaxエラーハンドリング
$(document).ajaxError(function(event, xhr, settings, error) {
    hideLoading();
    var message = 'エラーが発生しました。';
    if (xhr.responseJSON && xhr.responseJSON.message) {
        message = xhr.responseJSON.message;
    }
    showAlert('danger', message);
});

// パスワード強度チェック関数
function checkPasswordStrength(password) {
    var strength = 0;
    
    // 長さチェック
    if (password.length >= 8) strength += 25;
    if (password.length >= 12) strength += 25;
    
    // 大文字・小文字チェック
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength += 25;
    
    // 数字チェック
    if (/\d/.test(password)) strength += 15;
    
    // 特殊文字チェック
    if (/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) strength += 10;
    
    return strength;
}

// アラート表示
function showAlert(type, message) {
    var alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    $('.alert-container').html(alertHtml);
    // alert-info以外は自動消去
    if (type !== 'info') {
        setTimeout(function() {
            $('.alert:not(.alert-info)').fadeOut('slow');
        }, 5000);
    }
}