✦ Le support du son 5.1 surround a été implémenté et validé dans @MacNativeGames/games/totk/ avec détection automatique du matériel Mac et repli stéréo
  transparent.

  Détails des modifications apportées

   1. Conservation intégrale du 5.1 sans downmix (audio_mixer.c) :
      * Lorsque 6 canaux sont actifs, le mixer ne downmixe plus en stéréo : les 6 canaux discrets (FL, FR, Center, LFE, Surround Left, Surround Right) sont
        conservés sans aucune perte et le caisson de basses (LFE) n'est plus ignoré.
      * La configuration de l'AudioUnit applique la disposition standard CoreAudio kAudioChannelLayoutTag_AudioUnit_5_1 (qui correspond exactement à l'ordre des
        canaux de la Switch).

   2. Détection matérielle et repli stéréo sécurisé (output_open) :
      * Détection dynamique des capacités du périphérique de sortie par défaut via kAudioUnitProperty_StreamFormat sur le scope matériel.
      * Si le périphérique supporte au moins 6 canaux (home-cinéma HDMI, interface audio multicanal, etc.), le mode 5.1 s'active automatiquement.
      * Si l'initialisation 5.1 échoue (ou sur du matériel stéréo comme les haut-parleurs internes ou écouteurs), un fallback automatique en stéréo s'applique
        immédiatement avec le downmix matriciel logiciel ITU pour éviter toute coupure ou erreur -10868.
      * Une variable d'environnement permet également de forcer le comportement :
        * TOTK_AUDIO_CHANNELS=6 pour forcer le 5.1.
        * TOTK_AUDIO_CHANNELS=2 pour forcer le stéréo.

   3. Mise à jour du retour IPC (IAudioDevice::GetActiveChannelCount) :
      * La commande IPC (commande 5) renvoie désormais dynamiquement le nombre réel de canaux actifs (6 ou 2), informant ainsi le moteur audio interne du jeu de la
        configuration pour un rendu spatialisé optimal.

   4. Ring buffers et callback CoreAudio adaptés :
      * Le ring buffer (RING_FRAMES * 6), les buffers temporaires (output_scratch[MAX_FRAME * 6]), le callback pull() et l'enregistrement de capture diagnostique
        supportent désormais 2 ou 6 canaux de manière transparente.

   5. Tests de validation :
      * Un test dédié de routage 5.1 a été ajouté dans games/totk/tests/audio_routing/probe.c et validé avec succès (vérification bit-à-bit du respect des canaux
        discrets Center, LFE et Surround).