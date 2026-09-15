"""Tests for the MX/A/AAAA domain check in src/api/email_validation.py.

Nunca contra DNS real -- eso haria los tests dependientes de la red y del
estado actual de internet (mismo motivo por el que el resto de la suite evita
depender de un reloj real o una base de datos real cuando puede evitarlo).
Se simulan las respuestas de dnspython con mocks.
"""

from unittest.mock import MagicMock, patch

import dns.exception
import dns.resolver
import pytest

from src.api.email_validation import domain_can_receive_mail


def _fake_resolve(**by_rdtype):
    """Mock para Resolver.resolve que responde distinto segun el rdtype
    pedido (MX/A/AAAA) -- un valor real deja pasar, una excepcion se
    levanta tal cual. dnspython no hace binding de `self` cuando se
    reemplaza el metodo por un Mock, asi que la firma es (domain, rdtype)."""

    def _resolve(domain, rdtype):
        outcome = by_rdtype[rdtype]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    return MagicMock(side_effect=_resolve)


def test_accepts_domain_with_mx_record():
    mock_resolve = _fake_resolve(MX=["mx.example.com"])
    with patch.object(dns.resolver.Resolver, "resolve", mock_resolve):
        assert domain_can_receive_mail("gmail.com") is True

    # Encontro MX de una -- no hace falta ni consultar A ni AAAA.
    assert mock_resolve.call_count == 1


def test_rejects_domain_with_no_mx_a_or_aaaa():
    mock_resolve = _fake_resolve(
        MX=dns.resolver.NXDOMAIN(),
        A=dns.resolver.NXDOMAIN(),
        AAAA=dns.resolver.NXDOMAIN(),
    )
    with patch.object(dns.resolver.Resolver, "resolve", mock_resolve):
        assert domain_can_receive_mail("test.cadfa") is False

    assert mock_resolve.call_count == 3


def test_falls_back_to_a_record_when_domain_has_no_mx():
    """Un dominio chico puede recibir mail directo a su A sin MX explicito
    -- valido por RFC 5321, no hay que rechazarlo."""

    mock_resolve = _fake_resolve(MX=dns.resolver.NoAnswer(), A=["1.2.3.4"])
    with patch.object(dns.resolver.Resolver, "resolve", mock_resolve):
        assert domain_can_receive_mail("dominio-chico.com") is True

    assert mock_resolve.call_count == 2


def test_falls_back_to_aaaa_when_no_mx_or_a():
    mock_resolve = _fake_resolve(
        MX=dns.resolver.NoAnswer(),
        A=dns.resolver.NoAnswer(),
        AAAA=["::1"],
    )
    with patch.object(dns.resolver.Resolver, "resolve", mock_resolve):
        assert domain_can_receive_mail("solo-ipv6.com") is True

    assert mock_resolve.call_count == 3


def test_fails_open_on_dns_timeout():
    """Si el DNS no contesta a tiempo, no es culpa del usuario -- se deja
    pasar en vez de rechazar un email que podria ser perfectamente valido."""

    mock_resolve = _fake_resolve(MX=dns.exception.Timeout())
    with patch.object(dns.resolver.Resolver, "resolve", mock_resolve):
        assert domain_can_receive_mail("dominio-lento.com") is True

    # No sigue insistiendo con A/AAAA si el DNS ya esta fallando en si mismo.
    assert mock_resolve.call_count == 1


def test_fails_open_on_any_other_unexpected_dns_error():
    """Ej. un dominio con algun caracter que dnspython no pueda parsear como
    nombre DNS valido -- no es evidencia de que el email sea invalido, es un
    problema de la consulta en si."""

    mock_resolve = _fake_resolve(MX=RuntimeError("algo raro paso en dnspython"))
    with patch.object(dns.resolver.Resolver, "resolve", mock_resolve):
        assert domain_can_receive_mail("dominio-raro.com") is True

    assert mock_resolve.call_count == 1


def test_fails_open_when_no_nameservers_available():
    fake_request = MagicMock(question=["MX example.com"])
    mock_resolve = _fake_resolve(MX=dns.resolver.NoNameservers(request=fake_request, errors=[]))
    with patch.object(dns.resolver.Resolver, "resolve", mock_resolve):
        assert domain_can_receive_mail("dominio-cualquiera.com") is True


@pytest.mark.parametrize(
    "first_exception",
    [dns.resolver.NXDOMAIN(), dns.resolver.NoAnswer()],
)
def test_rejects_only_after_checking_all_three_record_types(first_exception):
    mock_resolve = _fake_resolve(
        MX=first_exception,
        A=dns.resolver.NoAnswer(),
        AAAA=dns.resolver.NXDOMAIN(),
    )
    with patch.object(dns.resolver.Resolver, "resolve", mock_resolve):
        assert domain_can_receive_mail("nada-de-nada.com") is False

    assert mock_resolve.call_count == 3
