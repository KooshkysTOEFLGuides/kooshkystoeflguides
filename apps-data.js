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
    name: "Listen and Repeat",
    href: "ListenAndRepeat/toefl_listen_repeat_practice.html",
    description: "Practise TOEFL Listen and Repeat sets, record your voice, and review your attempts.",
    logo: "ListenAndRepeat/icon.png",
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
