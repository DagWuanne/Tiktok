const login = require("fca-project-orion");
const fs = require("fs");

// Đọc AppState (Cookie dạng JSON)
const appState = JSON.parse(fs.readFileSync('appstate.json', 'utf8'));

login({ appState }, (err, api) => {
    if (err) return console.error("Lỗi đăng nhập: ", err);

    console.log("✅ Bot đã sẵn sàng test Name!");

    api.listenMqtt(async (err, event) => {
        if (err || event.type !== "message") return;

        const message = event.body ? event.body.toLowerCase() : "";

        if (message === "/fact") {
            const uid = event.senderID; // Lấy UID người nhắn

            try {
                // ĐOẠN CHECK NAME QUAN TRỌNG NHẤT
                const userInfo = await api.getUserInfo(uid);
                const name = userInfo[uid].name; 

                console.log(`--- CHECK THÀNH CÔNG ---`);
                console.log(`🆔 UID: ${uid}`);
                console.log(`👤 Name: ${name}`);
                console.log(`------------------------`);

                // Gửi phản hồi lại cho người đó để xác nhận
                api.sendMessage(`Chào ${name}!\nID của bạn là: ${uid}\nBot đã nhận diện được bạn thành công! 🐲`, event.threadID);
                
            } catch (e) {
                console.error("Lỗi lấy thông tin:", e);
            }
        }
    });
});
