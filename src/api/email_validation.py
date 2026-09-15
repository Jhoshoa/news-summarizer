from __future__ import annotations

import dns.resolver

# Tiempo maximo por consulta DNS individual -- si el resolver no contesta a
# tiempo, se asume que es un problema de red/DNS nuestro, no que el dominio
# sea invalido (ver domain_can_receive_mail).
DNS_TIMEOUT_SECONDS = 5.0


def _has_records(resolver: dns.resolver.Resolver, domain: str, rdtype: str) -> bool | None:
    """True/False si el DNS respondio algo concreto; None si no pudo
    responder de forma decisiva -- distinto de "no existe".

    Solo NXDOMAIN/NoAnswer cuentan como "no existe". Cualquier otra falla
    (timeout, sin nameservers, un dominio con algun caracter que dnspython
    no pueda parsear como nombre DNS valido, etc.) no es evidencia de que el
    dominio sea invalido -- se trata como inconclusa (None) para que
    domain_can_receive_mail falle abierto en vez de tirar un 500 o rechazar
    un email que podria ser perfectamente real."""

    try:
        resolver.resolve(domain, rdtype)
        return True
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return False
    except Exception:
        return None


def domain_can_receive_mail(domain: str) -> bool:
    """Best-effort: hay algun MX (o, a falta de eso, A/AAAA, valido por RFC
    5321 para dominios chicos sin MX explicito) para este dominio?

    Solo devuelve False ante una respuesta DNS explicita de "no existe" o
    "sin registros" -- ante cualquier falla de la consulta en si (timeout,
    resolver sin red) se falla abierto (True): no es responsabilidad del
    usuario que nuestro DNS haya tenido un mal momento.
    """

    resolver = dns.resolver.Resolver()
    resolver.timeout = DNS_TIMEOUT_SECONDS
    resolver.lifetime = DNS_TIMEOUT_SECONDS

    for rdtype in ("MX", "A", "AAAA"):
        result = _has_records(resolver, domain, rdtype)
        if result is not False:
            # True (hay registro) o None (no se pudo consultar) -> aceptar
            return True

    return False
