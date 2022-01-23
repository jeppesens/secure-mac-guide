This is a practical guide to using [YubiKey](https://www.yubico.com/faq/yubikey/) as a SmartCard for storing GPG encryption and signing keys. Keys stored on a SmartCard like YubiKey seem more difficult to steal than ones stored on disk, and are convenient for everyday use..

The blog "[Exploring Hard Tokens](https://www.avisi.nl/blog/2012/01/05/exploring-hard-tokens/)" describes the disadvantages of the combination of a username/password for access control. Passwords can be cracked or retrieved by social engineering. They can be read from faulty systems or even retrieved from unsecured internet access.

Authentication on a workstation often is done by using a username and password. Furthermore, it is almost impossible to detect when an attacker accesses a system. Therefore it is important to strengthen your authentication by adding a second step to your authentication process.

# Purchase YubiKey
We use the [YubiKey 5](https://www.yubico.com/products/yubikey-5-overview/)

You should also buy another YubiKey as a backup key for your computer login, because if you lose your YubiKey, you wont be able to login into your computer.

# Prepare your MacBook

## Enable full disk encryption
Please make sure before you start this process, that your Macbook has enabled FileVault 2 disk encryption.
Apple has an excellent guide here https://support.apple.com/en-gb/HT204837


## Enable Secure Keyboard Entry
Command line users who wish to add an additional layer of security to their keyboarding within Terminal app can find a helpful privacy feature built into the Mac client. Whether aiming for generally increasing security, if using a public Mac, or are simply concerned about things like keyloggers or any other potentially unauthorized access to your keystrokes and character entries, you can enable this feature in the Mac OS X Terminal app to secure keyboard entry and any command line input into the terminal.

### Mac builtin Terminal
Enable it for the build in Terminal on Macbook:

![SKI Terminal](http://cdn.osxdaily.com/wp-content/uploads/2011/12/secure-keyboard-entry.jpg "Terminal enable SKI")

## Enable firewall and stealth mode
Built-in, basic firewall which blocks incoming connections only.
> Note: this firewall does not have the ability to monitor, nor block outgoing connections.

![Enable firewall](/img/Firewall.png)
![Enable Stealth Mode](/img/Stealth.png)

Computer hackers scan networks so they can attempt to identify computers to attack. When stealth mode is enabled, your computer does not respond to ICMP ping requests, and does not answer to connection attempts from a closed TCP or UDP port.

# Install required software
The required software for this guide is:

* Homebrew
* PAM Yubico
* YubiKey Personalization Tools
* dnsmasq
* OpenSSL
* LibreSSL

## Install Homebrew
Open a Terminal window and then run the following command to install Homebrew:

```sh
/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
```

## Install better packages
The version of OpenSSL in Sierra is 0.9.8zh which is not current. It doesn't support TLS 1.1 or newer, elliptic curve ciphers, and more.

Apple declares OpenSSL deprecated in their Cryptographic Services Guide document. Their version also has patches which may surprise you.

The version of Curl which comes with macOS uses Secure Transport for SSL/TLS validation.

```sh
brew install openssl
brew install curl
brew install wget
```

### Configure your shell
To use LibreSSL and curl installed by Homebrew, it is important to update your path. You can add the following to your shell profile. Currently we're using zsh where the file you need to alter is `~/.zshrc`

Add the following to the file:

```sh
export PATH="/usr/local/opt/curl/bin:$PATH"
```

Or for Mac with M1 chips

```sh
export PATH="/opt/homebrew/opt/curl/bin:$PATH"
```

# DNS

## Install dnscrypt
DNSCrypt is a protocol that authenticates communications between a DNS client and a DNS resolver. It prevents DNS spoofing. It uses cryptographic signatures to verify that responses originate from the chosen DNS resolver and haven't been tampered with.

To install DNSCrypt proxy, run the following command:

```sh
brew install dnscrypt-proxy
```

Once installed, you need to change the listen port for the service. Edit the file `/opt/homebrew/etc/dnscrypt-proxy.toml` and change the following line:

```toml
listen_addresses = ['127.0.0.1:53']
```

to

```toml
listen_addresses = ['127.0.0.1:40']
```
This way, dnscrypt-proxy will listen on port 40 instead, since we use dnsmasq to listen on port 53 which is the default dns port.

Then change the following line:

```toml
server_names = ....
```

to

```toml
server_names = ['cloudflare', 'cloudflare-ipv6', 'dnscrypt-ip4-nofilter-pri', 'dnscrypt-ip4-nofilter-alt', ' dnscrypt-ip6-nofilter-pri', 'dnscrypt-ip6-nofilter-alt']
```

if you wanna resolve mongodb.net

and make sure the following code is uncommented:

```toml
  [sources.quad9-resolvers]
  urls = ['https://www.quad9.net/quad9-resolvers.md']
  minisign_key = 'RWQBphd2+f6eiAqBsvDZEBXBGHQBJfeG6G+wJPPKxCZMoEQYpmoysKUN'
  cache_file = 'quad9-resolvers.md'
  prefix = 'quad9-'
```

Restart dnscrypt-proxy to make the changes take affect:

```sh
sudo brew services restart dnscrypt-proxy
```

## Install dnsmasq
dnsmasq (short for DNS masquerade) is a lightweight, easy to configure DNS forwarder, designed to provide DNS (and optionally DHCP and TFTP) services to a small-scale network. It can serve the names of local machines which are not in the global DNS.

```sh
brew install dnsmasq
```

Once installed, you'll need to change to configuration of dnsmasq. If you add dnscrypt also, the following config works. If you do not use dnscrypt, you will need to change the servers address from 127.0.0.1#40 to 1.1.1.1

Alter the following file `/opt/homebrew/etc/dnsmasq.conf` and add the following content to the end of the file:

```conf
# For debugging purposes, log each DNS query as it passes through dnsmasq.
# If you wanna see the entries, uncomment the two lines below, and make sure that
# the folder /opt/homebrew/var/log/ exists
#log-queries=extra
#log-facility=/opt/homebrew/var/log/dnsmasq.log

listen-address=127.0.0.1
port=53
# you can add this but it will require macOS to allow incoming connections to dnsmasq and I cannot explain why
#interface=lo0
domain-needed
bogus-priv
no-resolv
no-hosts
no-poll
no-negcache
rebind-localhost-ok
strict-order
proxy-dnssec

local=/local/

# Custom development domains
address=/.dev/127.0.0.1
address=/.dom/127.0.0.1

# Upstream DNSCrypt
server=127.0.0.1#40
```

Restart dnsmasq to make sure changes are affected

```sh
sudo brew services restart dnsmasq
```

Then enable DNSMASQ for each interface on your Mac:

```sh
networksetup -listallnetworkservices 2>/dev/null | grep -v '*' | while read x ; do
    networksetup -setdnsservers "$x" 127.0.0.1 ::1
done
```

As an alternative, you can set the dns each time you open your terminal by adding:

```sh
# Set dns server to dnsmasq to force local cache
networksetup -setdnsservers "Wi-Fi" 127.0.0.1
```

to your `~/.zshrc` file - if you use ZSH.

### Block DNS queries
You should block all connections to other DNS servers as various programs use some sort of internal DNS resolver. Chrome has this build in, lots of programs also falls back to systemd's resolver. So to make sure we always use Stubby as DNS resolver, we simply just block all DNS connections to anything but Knot Resolver:

Start of by editing `/etc/pf.conf` and add the following snippet between `dummynet-anchor "com.apple/*"` and `dummynet-anchor "com.apple/*"` since pf is sensitive about the order of rules

```pf
### TO REROUTE DNS TO LOCALHOST
# A macro to shorten rules below, catches outgoing tcp and udp traffic on port 53
Packets = "proto { udp, tcp } from en0 to any port 53"

# Rule 1: Redirect those connections after they were routed to lo0 below
rdr pass log on lo0 $Packets -> 127.0.0.1

# Rule 2: Route new IPv4 connections leaving en0 to lo0
pass out on en0 route-to lo0 inet $Packets
### TO REROUTE DNS TO LOCALHOST
```
_PS. if you're using something like Little Snitch, it will look like the connections are going to something other than 127.0.0.1 (e.g 8.8.8.8) because it is rerouted after the filter from Little Snitch_

Then reload the firewall with:

```sh
sudo pfctl -ef /etc/pf.conf
```

Verify that the rule is active with:
```sh
pfctl -v -s rules
```

### Test dns
A quick test can be done by using dig (or your favorite DNS tool) on the loopback address

```sh
dig @127.0.0.1 www.example.com

; <<>> DiG 9.9.7-P3 <<>> @127.0.0.1 www.example.com
; (1 server found)
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 52807
;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 2, ADDITIONAL: 1

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 4096
; OPT=8: 00 00 00 00  (.) (.) (.) (.)
;; QUESTION SECTION:
;www.example.com.		IN	A

;; ANSWER SECTION:
wWW.ExAmPLe.com.	27319	IN	A	93.184.216.34

;; AUTHORITY SECTION:
ExAmPLe.com.		1751	IN	NS	b.iana-servers.net.
ExAmPLe.com.		1751	IN	NS	a.iana-servers.net.

;; Query time: 226 msec
;; SERVER: 127.0.0.1#53(127.0.0.1)
;; WHEN: Mon Oct 30 09:56:58 CET 2017
;; MSG SIZE  rcvd: 169
```

You should also test and make sure you cannot use external DNS servers. The following should give you a timeout:

```sh
dig @8.8.8.8 www.example.com

; <<>> DiG 9.10.6 <<>> @8.8.8.8 www.example.com
; (1 server found)
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 41135
;; flags: qr rd ra ad; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 1232
;; QUESTION SECTION:
;www.example.com.		IN	A

;; ANSWER SECTION:
www.example.com.	77180	IN	A	93.184.216.34

;; Query time: 4195 msec
;; SERVER: 8.8.8.8#53(8.8.8.8)
;; WHEN: Sat Jan 22 21:55:19 CET 2022
;; MSG SIZE  rcvd: 60
```

## Install YubiKey Personalization Tools
Install the latest version of the YubiKey Personalization Tool

https://www.yubico.com/products/services-software/download/yubikey-personalization-tools/

# Configure your YubiKey
Open the YubiKey Personalization Tool from your program folder on your MacBook and insert the YubiKey in a USB port on your Mac.

1. Open the "Settings tab at the top of the window, and ensure that the "Logging Settings"
section has logging enabled, and the “Yubico Format“ selected.

2. Open the “Challenge Response” tab at the top of the window. Then configure slot 2:

  1. Select Configuration Slot 2
  2. Select Variable input for HMAC-SHA1 Mode
  3. Click Generate to generate a new Secret Key (20 bytes Hex)
  4. Make sure it the box is `unchecked` for "Require user input (button press)"
  5. Click Write Configuration

![Set Yubikey options](https://crewjam.com/images/YubiKey_Personalization_Tool_and_MacOS_X_Challenge-Response.png "YubiKey Personalization Tool")

You must configure both the YubiKeys with the Challenge-Response mode now.

# Install PAM Yubico
Open a Terminal window, and run the following command:
```sh
brew install pam_yubico
```

## Configure PAM on your Macbook
Open a Terminal window, and run the following command as your regular user, with firstly the YubiKey inserted.

> Note: If you have secure keyboard input enabled for your terminal, this will give an error. Disable while you run the commands and reenable it.

```sh
mkdir –p ~/.yubico
chmod -R 0700 ~/.yubico
ykpamcfg -2
```

Your YubiKey are now setup with your MacBook and can be used. You should store the backup YubiKey somewhere safe for recovery - like in a vault in your bank ;)

## Enable YubiKey for Auth, Sudo and Screensaver
Before you proceed, you should verify you have the `/usr/local/lib/security/pam_yubico.so` or `/opt/homebrew/lib/security/pam_yubico.so` file present on your Macbook from your earlier preparations. If you dont, you will lock your self out of your Macbook now.

Edit the following files:

* /etc/pam.d/authorization
* /etc/pam.d/sudo
* /etc/pam.d/screensaver

You need to use sudo to do so. From the terminal issue the following command:

```
sudo vi /etc/pam.d/screensaver
```

Add the following to the file:

```
auth       required       /usr/local/lib/security/pam_yubico.so mode=challenge-response
```

Or below for Mac's with M1

```
auth       required       /opt/homebrew/lib/security/pam_yubico.so mode=challenge-response
```

Ending up with something like this

```
auth       optional       pam_krb5.so use_first_pass use_kcminit
auth       required       pam_opendirectory.so use_first_pass nullok
auth       required       /usr/local/lib/security/pam_yubico.so mode=challenge-response
account    required       pam_opendirectory.so
account    sufficient     pam_self.so
account    required       pam_group.so no_warn group=admin,wheel fail_safe
account    required       pam_group.so no_warn deny group=admin,wheel ruser fail_safe
```

Also remember to set the screensaver to require password or it wont work anyway :)

![Mac screensaver](https://i.stack.imgur.com/BwMhk.png "Macbook Screensaver Password")

Before you alter the `sudo` and `authorization` files, you can verify everything works by enabling the screensaver first. If you cannot login from the screensaver while the YubiKey is present, something is terrible wrong now and you should NOT continue.

Use the screensaver to check both the YubiKeys before you proceed.

## Change PINs
The default PIN codes are `12345678` for admin and `123456` for default use. You will need to use the default pin on everyday basis when you need to use the ssh key for auth. The Admin key is only if you want to alter data on the card.

Do not lose these pins EVER or you'll have to reset the card with the included `yubikey-reset.sh` script in this repo.

```
gpg/card> admin
Admin commands are allowed

gpg/card> passwd
gpg: OpenPGP card no. D2760001240102010006055532110000 detected

1 - change PIN
2 - unblock PIN
3 - change Admin PIN
4 - set the Reset Code
Q - quit

Your selection? 3
PIN changed.

1 - change PIN
2 - unblock PIN
3 - change Admin PIN
4 - set the Reset Code
Q - quit

1 - change PIN
2 - unblock PIN
3 - change Admin PIN
4 - set the Reset Code
Q - quit

Your selection? 1
PIN changed.

1 - change PIN
2 - unblock PIN
3 - change Admin PIN
4 - set the Reset Code
Q - quit

Your selection? q
```

# Misc
Different information and help.

## Loss of Yubikey
In case you lose your YubiKey, everything is not yet over and data is not yet lost. If you have another YubiKey nearby, you can simply redeploy the secure keys to a new YubiKey.

# References
* https://florin.myip.org/blog/easy-multifactor-authentication-ssh-using-yubikey-neo-tokens
* https://getdnsapi.net/blog/dns-privacy-daemon-stubby/
* https://dnsprivacy.org/wiki/pages/viewpage.action?pageId=3145812
