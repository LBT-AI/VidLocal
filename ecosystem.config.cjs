module.exports = {
  apps: [
    {
      name: "vidlocal-compose",
      cwd: "/root/vidlocal",
      script: "docker",
      args: "compose up",
      interpreter: "none",
      autorestart: true,
      restart_delay: 5000,
      max_restarts: 10,
      kill_timeout: 30000,
      time: true,
    },
  ],
};
