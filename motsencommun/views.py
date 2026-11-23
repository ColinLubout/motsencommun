"""Pages du projet hors du lexique."""

import datetime

from django.conf import settings
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

#: security.txt doit dire jusqu'à quand il reste valable (RFC 9116, au plus un an).
VALIDITE_DE_SECURITY_TXT = datetime.timedelta(days=180)


def security_txt(request):
    """/.well-known/security.txt : où signaler une faille, en privé (RFC 9116)."""
    expiration = (timezone.now() + VALIDITE_DE_SECURITY_TXT).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return render(
        request,
        "security.txt",
        {
            "contact": f"{settings.DEPOT_DU_CODE}/security/advisories/new",
            "politique": f"{settings.DEPOT_DU_CODE}/blob/main/SECURITY.md",
            "expiration": expiration.astimezone(datetime.UTC).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "adresse": request.build_absolute_uri(reverse("security_txt")),
        },
        content_type="text/plain; charset=utf-8",
    )
