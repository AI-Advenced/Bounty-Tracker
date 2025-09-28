module.exports = {
  apps: [
    {
      name: 'bounty-tracker',
      script: 'python',
      args: '-m uvicorn simple_app:app --host 0.0.0.0 --port 3000 --reload',
      cwd: '/home/user/webapp',
      env: {
        NODE_ENV: 'development',
        PORT: 3000,
        DATABASE_URL: 'sqlite:///./bounty_tracker.db',
        DATABASE_ECHO: 'false',
        SECRET_KEY: 'bounty-tracker-secret-key-change-in-production',
        ACCESS_TOKEN_EXPIRE_MINUTES: '30',
        REFRESH_TOKEN_EXPIRE_DAYS: '7'
      },
      watch: false,
      instances: 1,
      exec_mode: 'fork',
      max_restarts: 10,
      min_uptime: '10s',
      error_file: './logs/err.log',
      out_file: './logs/out.log',
      log_file: './logs/combined.log',
      time: true
    }
  ]
};