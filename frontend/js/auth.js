import { api, showToast, requireGuest } from "./api.js";

// =========================================
// REGISTER
// =========================================
document.addEventListener("DOMContentLoaded", function () {
  const registerForm = document.getElementById("registerForm");
  if (registerForm) {
    requireGuest();
    registerForm.addEventListener("submit", handleRegister);
  }

  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    requireGuest();
    loginForm.addEventListener("submit", handleLogin);
  }
});

async function handleRegister(e) {
  e.preventDefault();

  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;
  const confirmPassword = document.getElementById("confirmPassword").value;
  const fullname = document.getElementById("fullname").value.trim();
  const email = document.getElementById("email").value.trim();

  if (!username || !password || !fullname || !email) {
    showToast("Vui lòng điền đầy đủ thông tin", "error");
    return;
  }

  if (password !== confirmPassword) {
    showToast("Mật khẩu không khớp", "error");
    return;
  }

  if (password.length < 6) {
    showToast("Mật khẩu phải có ít nhất 6 ký tự", "error");
    return;
  }

  try {
    const result = await api.register(username, password, fullname, email);

    if (result.success) {
      showToast("Đăng ký thành công! Vui lòng đăng nhập", "success");
      setTimeout(() => {
        window.location.href = "login.html";
      }, 1500);
    } else {
      showToast(result.message || "Đăng ký thất bại", "error");
    }
  } catch (error) {
    showToast("Có lỗi xảy ra, vui lòng thử lại", "error");
    console.error(error);
  }
}

// =========================================
// LOGIN - QUAN TRỌNG: Chuyển trang sau login
// =========================================
async function handleLogin(e) {
  e.preventDefault();

  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;

  if (!username || !password) {
    showToast("Vui lòng nhập tên đăng nhập và mật khẩu", "error");
    return;
  }

  try {
    const result = await api.login(username, password);
    console.log("Login result:", result); // Debug

    if (result.success) {
      showToast("Đăng nhập thành công!", "success");

      // Lưu token và user vào localStorage
      localStorage.setItem("token", result.token);
      localStorage.setItem("user", JSON.stringify(result.user));

      // CHUYỂN TRANG SAU 1 GIÂY
      setTimeout(() => {
        window.location.href = "dashboard.html";
      }, 1000);
    } else {
      showToast(result.message || "Đăng nhập thất bại", "error");
    }
  } catch (error) {
    console.error("Login error:", error);
    showToast("Có lỗi xảy ra, vui lòng thử lại", "error");
  }
}

// =========================================
// LOGOUT
// =========================================
window.logout = function () {
  api.logout();
  showToast("Đã đăng xuất", "info");
  setTimeout(() => {
    window.location.href = "login.html";
  }, 500);
};

// =========================================
// TOGGLE PASSWORD
// =========================================
window.togglePassword = function (element) {
  const input = element.parentElement.querySelector("input");
  if (input.type === "password") {
    input.type = "text";
    element.classList.remove("fa-eye");
    element.classList.add("fa-eye-slash");
  } else {
    input.type = "password";
    element.classList.remove("fa-eye-slash");
    element.classList.add("fa-eye");
  }
};

// =========================================
// CHECK AUTH ON PAGE LOAD
// =========================================
document.addEventListener("DOMContentLoaded", function () {
  // Kiểm tra nếu đã đăng nhập thì chuyển đến dashboard
  const token = localStorage.getItem("token");
  const user = localStorage.getItem("user");

  if (token && user) {
    // Nếu đang ở login/register thì chuyển sang dashboard
    const currentPath = window.location.pathname;
    if (
      currentPath.includes("login.html") ||
      currentPath.includes("register.html")
    ) {
      window.location.href = "dashboard.html";
    }
  }
});
