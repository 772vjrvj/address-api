module.exports = {
    apps: [
        {
            name: "address-api-blue",
            cwd: "E:/git/address-api",
            script: "run.py",
            interpreter: "E:/git/address-api/venv/Scripts/python.exe",
            env: {
                SERVER_HOST: "127.0.0.1",
                SERVER_PORT: "5101",
                WAITRESS_THREADS: "4"
            }
        },
        {
            name: "address-api-green",
            cwd: "E:/git/address-api",
            script: "run.py",
            interpreter: "E:/git/address-api/venv/Scripts/python.exe",
            env: {
                SERVER_HOST: "127.0.0.1",
                SERVER_PORT: "5102",
                WAITRESS_THREADS: "4"
            }
        }
    ]
};