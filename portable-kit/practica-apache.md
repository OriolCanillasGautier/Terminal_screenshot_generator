# Practica: Apache HTTP + Seguretat + Virtual Hosts + Vulnerabilitats

**10/05/2026 · Ubuntu 25.10 · Apache 2.4.64 · PHP 8.4**

---

## 1. Xarxa interna + DNS + DHCP

Segona interfície (enp0s8) com a xarxa interna 192.168.100.0/24. BIND resol `oriol.canillas.local` amb registres per `exercici3` i `exercici4`. DHCP serveix IPs .50-.200 al domini `oriol.canillas.local`.

![01](01-screenshot.png)

![02](02-screenshot.png)

---

## 2. Apache: hardening de seguretat

Fitxer `/etc/apache2/conf-available/security-hardening.conf`:

- *ServerTokens Prod* + *ServerSignature Off*: oculta la versio
- *TraceEnable Off*: evita Cross-Site Tracing
- *Options -Indexes*: desactiva el llistat de directoris
- *Require all denied* a `/`: denega acces per defecte
- *FilesMatch*: bloqueja `.htaccess` i `.htpasswd` des del navegador
- Usuari `www-data` amb privilegis minims
- SSL amb certificat auto-signat. Moduls: `ssl`, `rewrite`, `php8.4`

![03](03-screenshot.png)

---

## 3. Exercici 3: carpeta protegida + bypass amb PHP include

Carpeta `/protegida/` amb `.htaccess` (`Require all denied`). L'acces directe retorna *403 Forbidden*.

Un `index.php` amb `include($_GET['document'])` permet llegir `protegida/arxiu.php` via `?document=protegida/arxiu.php`.

![04](04-screenshot.png)

---

## 4. Exercici 4: carpeta amb htpasswd

Carpeta `/restringit/` protegida amb autenticacio Basic (`.htpasswd`). Credencials: `oriol` / `secret`. Sense autenticacio retorna *401 Unauthorized*.

![05](05-screenshot.png)

---

## 5. Exercici 5: Code Injection

Script PHP vulnerable: `system($_GET['cmd'])` sense validacio. Permet executar qualsevol comanda com a `www-data` (`id`, `whoami`, `cat /etc/passwd`...).

La mitigacio: `escapeshellcmd()` o llista blanca d'entrada.

![06](06-screenshot.png)

---

## 6. Virtual hosts configurats

Llistat dels sites habilitats: `000-default`, `exercici3`, `exercici4`, `default-ssl`.

![07](07-screenshot.png)

---

## 7. Proves des del client (noms DNS reals)

Un client a la xarxa interna (192.168.100.0/24) amb DHCP i DNS configurats
pot accedir als virtual hosts pels seus noms DNS reals, sense necessitat de
capcalera `Host`:

- *curl http://exercici3.oriol.canillas.local/protegida/arxiu.php* → 403
- *curl 'http://exercici3.oriol.canillas.local/index.php?document=protegida/arxiu.php'* → mostra contingut
- *curl http://exercici4.oriol.canillas.local/restringit/* → 401
- *curl -u oriol:secret http://exercici4.oriol.canillas.local/restringit/* → OK
- *curl 'http://oriol.canillas.local/code_injection.php?cmd=id'* → code injection

![08](08-client-test.png)

---

## 8. Conclusions

1. L'enduriment d'Apache es fa amb poques directives: ocultar versio, desactivar TRACE i -Indexes, restringir directoris.
2. Els `.htaccess` protegeixen directoris pero un `include()` PHP sense validar pot eludir la proteccio.
3. L'autenticacio Basic amb `.htpasswd` es senzilla pero les credencials viatgen en pla; cal HTTPS.
4. `system()` sense sanejar l'input es extremadament perillos.
5. El firewall no es la solucio per problemes d'aplicacio web; la seguretat s'aplica al servidor i al codi.
