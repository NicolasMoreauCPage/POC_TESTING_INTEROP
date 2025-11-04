"""
Service de mise à jour automatique des dates dans les scénarios IHE.

Ce module permet de recalculer les dates des messages HL7 pour qu'elles soient
toujours récentes, car beaucoup de systèmes hospitaliers rejettent les messages
avec des dates dans le passé.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional


def update_hl7_message_dates(message: str, reference_time: Optional[datetime] = None) -> str:
    """
    Met à jour les dates dans un message HL7 pour les rendre récentes.
    
    Stratégie :
    - Détecte la date la plus ancienne dans le message (MSH-7, PID-7, PV1-44, etc.)
    - Calcule le décalage entre cette date et maintenant
    - Applique ce décalage à toutes les dates du message
    
    Args:
        message: Message HL7 (segments séparés par \\r ou \\n)
        reference_time: Temps de référence (par défaut: datetime.utcnow())
    
    Returns:
        Message HL7 avec dates mises à jour
    
    Example:
        >>> msg = "MSH|^~\\&|SRC|FAC|DST|FAC|20200101120000||ADT^A01|123|P|2.5"
        >>> updated = update_hl7_message_dates(msg)
        >>> # Les dates seront remplacées par des dates récentes
    """
    if reference_time is None:
        reference_time = datetime.utcnow()
    
    # Pattern pour détecter les timestamps HL7 (YYYYMMDD[HHMMSS[.SSSS]][+/-ZZZZ])
    # Exemples: 20221016, 20221016235900, 20221016235900.1234, 20221016235900+0100
    timestamp_pattern = re.compile(
        r'\b(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])'  # Date: YYYYMMDD
        r'(?:([01]\d|2[0-3])([0-5]\d)([0-5]\d))?'           # Heure optionnelle: HHMMSS
        r'(?:\.(\d{1,4}))?'                                 # Millisecondes optionnelles
        r'(?:([+-]\d{4}))?'                                 # Timezone optionnelle
        r'\b'
    )
    
    # Trouver toutes les dates dans le message
    dates_found = []
    for match in timestamp_pattern.finditer(message):
        try:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            hour = int(match.group(4)) if match.group(4) else 0
            minute = int(match.group(5)) if match.group(5) else 0
            second = int(match.group(6)) if match.group(6) else 0
            
            dt = datetime(year, month, day, hour, minute, second)
            dates_found.append((match.group(0), dt, match.span()))
        except (ValueError, TypeError):
            # Date invalide, on ignore
            continue
    
    if not dates_found:
        # Pas de dates trouvées, retourner le message tel quel
        return message
    
    # Trouver la date la plus ancienne (date de référence du scénario)
    oldest_date = min(dates_found, key=lambda x: x[1])[1]
    
    # Calculer le décalage à appliquer
    time_shift = reference_time - oldest_date
    
    # Remplacer toutes les dates en appliquant le décalage
    # On traite les dates de la fin vers le début pour préserver les positions
    result = message
    for original_str, original_dt, (start, end) in reversed(dates_found):
        new_dt = original_dt + time_shift
        
        # Reconstruire le timestamp HL7 en préservant le format original
        if len(original_str) == 8:  # YYYYMMDD
            new_str = new_dt.strftime("%Y%m%d")
        elif len(original_str) == 14:  # YYYYMMDDHHMMSS
            new_str = new_dt.strftime("%Y%m%d%H%M%S")
        else:
            # Format complet avec potentiellement millisecondes et timezone
            new_str = new_dt.strftime("%Y%m%d%H%M%S")
            # Copier les millisecondes et timezone si présentes
            if '.' in original_str:
                ms_part = original_str.split('.')[1].split('+')[0].split('-')[0]
                new_str += '.' + ms_part
            if '+' in original_str or (original_str.count('-') > 2):
                tz_part = original_str[-5:] if ('+' in original_str[-5:] or '-' in original_str[-5:]) else ''
                if tz_part:
                    new_str += tz_part
        
        result = result[:start] + new_str + result[end:]
    
    return result


def calculate_relative_datetime(
    reference_time: datetime,
    days_offset: int = 0,
    hours_offset: int = 0,
    minutes_offset: int = 0,
) -> datetime:
    """
    Calcule une date/heure relative à une référence.
    
    Utile pour créer des séquences de mouvements avec des délais relatifs.
    
    Args:
        reference_time: Temps de référence (généralement datetime.utcnow())
        days_offset: Nombre de jours à ajouter/soustraire
        hours_offset: Nombre d'heures à ajouter/soustraire
        minutes_offset: Nombre de minutes à ajouter/soustraire
    
    Returns:
        Datetime calculée
    
    Example:
        >>> now = datetime.utcnow()
        >>> admission = calculate_relative_datetime(now, days_offset=-2)  # Il y a 2 jours
        >>> mouvement = calculate_relative_datetime(now, hours_offset=-1)  # Il y a 1 heure
    """
    delta = timedelta(days=days_offset, hours=hours_offset, minutes=minutes_offset)
    return reference_time + delta


def format_hl7_datetime(dt: datetime, include_seconds: bool = True) -> str:
    """
    Formate une datetime Python en timestamp HL7.
    
    Args:
        dt: Datetime à formater
        include_seconds: Si True, inclut HHMMSS, sinon juste YYYYMMDD
    
    Returns:
        String au format HL7 (YYYYMMDD ou YYYYMMDDHHMMSS)
    
    Example:
        >>> dt = datetime(2022, 10, 16, 23, 59, 0)
        >>> format_hl7_datetime(dt)
        '20221016235900'
        >>> format_hl7_datetime(dt, include_seconds=False)
        '20221016'
    """
    if include_seconds:
        return dt.strftime("%Y%m%d%H%M%S")
    return dt.strftime("%Y%m%d")


def parse_hl7_datetime(hl7_str: str) -> Optional[datetime]:
    """
    Parse une date/heure HL7 en datetime Python.
    
    Args:
        hl7_str: String au format HL7 (YYYYMMDD[HHMMSS[.SSSS]][+/-ZZZZ])
    
    Returns:
        Datetime parsée ou None si invalide
    
    Example:
        >>> parse_hl7_datetime("20221016235900")
        datetime(2022, 10, 16, 23, 59, 0)
        >>> parse_hl7_datetime("20221016")
        datetime(2022, 10, 16, 0, 0, 0)
    """
    # Nettoyer la chaîne (retirer timezone et millisecondes pour simplifier)
    clean_str = hl7_str.split('.')[0].split('+')[0].split('-')[0]
    
    try:
        if len(clean_str) == 8:  # YYYYMMDD
            return datetime.strptime(clean_str, "%Y%m%d")
        elif len(clean_str) == 14:  # YYYYMMDDHHMMSS
            return datetime.strptime(clean_str, "%Y%m%d%H%M%S")
        elif len(clean_str) >= 10:  # YYYYMMDDHH[MM[SS]]
            # Compléter avec des zéros
            padded = clean_str.ljust(14, '0')
            return datetime.strptime(padded[:14], "%Y%m%d%H%M%S")
    except (ValueError, TypeError):
        pass
    
    return None


# Fonction helper pour les tests et debugging
def analyze_message_dates(message: str) -> dict:
    """
    Analyse les dates présentes dans un message HL7.
    
    Utile pour diagnostiquer les problèmes de dates dans les messages.
    
    Args:
        message: Message HL7
    
    Returns:
        Dictionnaire avec statistiques sur les dates trouvées
    """
    timestamp_pattern = re.compile(
        r'\b(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])'
        r'(?:([01]\d|2[0-3])([0-5]\d)([0-5]\d))?'
        r'(?:\.(\d{1,4}))?'
        r'(?:([+-]\d{4}))?'
        r'\b'
    )
    
    dates = []
    for match in timestamp_pattern.finditer(message):
        dt = parse_hl7_datetime(match.group(0))
        if dt:
            dates.append({
                'string': match.group(0),
                'datetime': dt,
                'position': match.span(),
                'segment': message[max(0, match.start() - 10):match.start()].split('\r')[-1].split('\n')[-1][:3]
            })
    
    if not dates:
        return {
            'count': 0,
            'oldest': None,
            'newest': None,
            'dates': []
        }
    
    sorted_dates = sorted(dates, key=lambda x: x['datetime'])
    
    return {
        'count': len(dates),
        'oldest': sorted_dates[0]['datetime'],
        'newest': sorted_dates[-1]['datetime'],
        'span_days': (sorted_dates[-1]['datetime'] - sorted_dates[0]['datetime']).days,
        'dates': dates
    }
