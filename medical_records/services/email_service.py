from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

def send_share_email(*, to_email: str, to_name: str, from_name: str, record_id: int):
    subject = "[TabibLink] Un dossier médical vous a été partagé"

    shared_url = f"{settings.FRONTEND_URL}/medical-records/shared"

    text_content = (
        f"Bonjour {to_name},\n\n"
        f"Le Dr {from_name} a partagé un dossier médical avec vous.\n"
        f"Accédez à vos dossiers partagés ici: {shared_url}\n\n"
        f"Record ID: {record_id}\n"
        f"— TabibLink\n"
    )

    html_content = f"""
    <div style="font-family: Arial, sans-serif; background:#f6f9fc; padding:24px;">
      <div style="max-width:600px; margin:0 auto; background:#ffffff; border-radius:12px; padding:24px; border:1px solid #e6eef7;">
        <h2 style="margin:0 0 12px 0; color:#1f2937;">📄 Dossier médical partagé</h2>
        <p style="margin:0 0 12px 0; color:#374151; font-size:14px;">
          Bonjour <b>{to_name}</b>,
        </p>
        <p style="margin:0 0 16px 0; color:#374151; font-size:14px;">
          Le Dr <b>{from_name}</b> a partagé un dossier médical avec vous.
        </p>
        <div style="margin:0 0 18px 0; padding:12px; background:#f3f4f6; border-radius:8px; font-size:13px; color:#111827;">
          <b>Record ID:</b> {record_id}
        </div>
        <a href="{shared_url}"
           style="display:inline-block; background:#2563eb; color:#ffffff; text-decoration:none;
                  padding:12px 18px; border-radius:10px; font-weight:bold; font-size:14px;">
          Voir mes dossiers partagés
        </a>
        <p style="margin:18px 0 0 0; color:#6b7280; font-size:12px;">
          Si le bouton ne marche pas, copiez-collez ce lien dans votre navigateur :<br/>
          <span style="color:#2563eb;">{shared_url}</span>
        </p>
        <hr style="border:none; border-top:1px solid #e5e7eb; margin:18px 0;" />
        <p style="margin:0; color:#9ca3af; font-size:12px;">
          © {timezone.now().year} TabibLink — Plateforme sécurisée de partage de dossiers médicaux
        </p>
      </div>
    </div>
    """

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    msg.attach_alternative(html_content, "text/html")

    # optionnel: voir les erreurs au lieu de les cacher
    msg.send(fail_silently=False)
