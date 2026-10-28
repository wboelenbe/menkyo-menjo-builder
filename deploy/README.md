# Deploying Menkyo on an OVH VPS

Result: `https://your-hostname/` shows the certificate form, behind a
username and password. Nothing is stored except the dōjō's settings.

## What you need
- An OVH VPS running Ubuntu 22.04/24.04 or Debian 12, **at least 4 GB RAM**
  (a render can use 1-2 GB; add swap below if you have less).
- A hostname pointing at it. HTTPS needs one: a domain you own, or a free
  subdomain from a dynamic-DNS service. Create an **A record** for it with the
  VPS's IPv4 address (shown in the OVH control panel). Do this first, because
  DNS can take a while.

## 1. Prepare the server
```
ssh ubuntu@YOUR_VPS_IP          # OVH shows the default user in the welcome email
sudo apt update && sudo apt -y upgrade
sudo ufw allow OpenSSH && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw --force enable
```
Optional 2 GB swap, a safety net for big renders:
```
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 2. Install Docker
Docker's own installer script (it sets up their apt repository and the
Compose plugin):
```
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER     # then log out and back in
docker compose version            # check
```

## 3. Get the code and configure
```
git clone https://github.com/OWNER/menkyo-menjo-builder.git
cd menkyo-menjo-builder
cp deploy/.env.example deploy/.env
docker run --rm caddy:2 caddy hash-password      # type a password, copy the hash
nano deploy/.env                                 # DOMAIN, AUTH_USER, AUTH_HASH (in 'single quotes')
```

## 4. Start
```
docker compose -f deploy/docker-compose.yml up -d --build
docker compose -f deploy/docker-compose.yml logs -f      # Ctrl-C to leave
```
The first build takes several minutes (Inkscape is large). Then open
`https://your-hostname/`. Caddy fetches the certificate on first request; if
it fails, check that the A record has propagated and that ports 80 and 443 are
open (also in the OVH panel, if you enabled a firewall there).

## 5. Check these once
- **Fonts.** The crest lettering needs the Noto Serif CJK JP font:
  `docker compose -f deploy/docker-compose.yml exec menkyo fc-list | grep "Noto Serif CJK JP"`
  should list a SemiBold. If the build printed a WARNING about it, tell me.
- **Output matches your Mac.** The server's Inkscape (Debian ships 1.2.x) may be
  a different version from yours. Generate one certificate here and one with
  the command line on your Mac and compare them at print size before
  printing a real batch.

## Day-to-day
- Update: `git pull && docker compose -f deploy/docker-compose.yml up -d --build`
- Settings are in the `menkyo-data` volume (`dojo.toml`); they survive updates.
  Back up with:
  `docker run --rm -v deploy_menkyo-data:/d -v $PWD:/b busybox cp /d/Menkyo/dojo.toml /b/`
  (the volume name is `<folder>_menkyo-data`; see `docker volume ls`).
- Change the password: make a new hash, edit `deploy/.env`, then
  `docker compose -f deploy/docker-compose.yml up -d`.
- If a render dies with a memory error, add swap (step 1) or move to a larger VPS.
