/*
  EDIT THIS FILE TO MANAGE THE APPS PAGE.

  Add one object per app. Delete an object to remove it.
  Set featured: true to show it on the homepage.

  Required:
    name: app name
    href: path to the app's starting HTML file
    description: a short description

  Optional:
    logo: path to a square image
    featured: true or false

  If logo is missing, empty, or cannot be loaded, the site uses the main
  Kooshky logo automatically.

  App order on both pages is exactly the order used in this array.
*/

window.KOOSHKY_APPS = [
  {
    name: "Fill The Blanks",
    href: "Apps/FillTheBlanks/kooshky_toefl_complete_the_words.html",
    description: "Practice fill the blanks exercises",
    logo: "Apps/FillTheBlanks/icon.png",
    featured: true
  },
  {
    name: "Word Stats",
    href: "Apps/WordStats/real_toefl_word_stats.html",
    description: "Find out how many times each word has appeared in real TOEFL tests, both new and old formats!",
    logo: "Apps/WordStats/icon.png",
    featured: true
  },
  {
    name: "Emails",
    href: "Apps/Emails/kooshky_toefl_email_practice.html",
    description: "Realistic, standard TOEFL Write an Email Prompts",
    logo: "Apps/Emails/icon.png",
    featured: true
  },
  {
    name: "Academic Discussion",
    href: "Apps/AcademicDiscussion/toefl_academic_discussion_simulator.html",
    description: "Realistic, standard TOEFL Academic Discussion Prompts",
    logo: "Apps/AcademicDiscussion/icon.png",
    featured: true
  },
  {
    name: "Dictation",
    href: "Apps/Dictation/kooshky_dictation_practice.html",
    description: "Practise spelling using the Leitner Method! This is Jhoana's section.",
    logo: "Apps/Dictation/icon.png",
    featured: true
  },
  {
    name: "Listen and Repeat",
    href: "Apps/ListenAndRepeat/toefl_listen_repeat_practice.html",
    description: "Practise TOEFL Listen and Repeat sets, record your voice, and review your attempts.",
    logo: "Apps/ListenAndRepeat/icon.png",
    featured: true
  },
  /*
  {
    name: "Listen and Repeat Simulator",
    href: "Apps/ListenAndRepeat/index.html",
    description: "Practise TOEFL Listen and Repeat sets, record your voice, and review your attempts.",
    logo: "Apps/ListenAndRepeat/icon.png",
    featured: true
  },
  {
    name: "Dictation Practice",
    href: "Apps/Dictation/index.html",
    description: "A simple tool for practising English dictation with audio.",
    featured: true
  }
  */
];
