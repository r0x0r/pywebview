# Loading animation

Create a loading animation that is displayed before application is loaded.


``` python
import webview


html = """
    <style>
        body {
            background-color: #333;
            color: white;
            font-family: Helvetica Neue, Helvetica, Arial, sans-serif;
        }

        .main-container {
            width: 100%;
            height: 90vh;
            display: flex;
            display: -webkit-flex;
            align-items: center;
            -webkit-align-items: center;
            justify-content: center;
            -webkit-justify-content: center;
            overflow: hidden;
        }

        .loading-container {
        }

        .loader {
          font-size: 10px;
          margin: 50px auto;
          text-indent: -9999em;
          width: 3rem;
          height: 3rem;
          border-radius: 50%;
          background: #ffffff;
          background: -moz-linear-gradient(left, #ffffff 10%, rgba(255, 255, 255, 0) 42%);
          background: -webkit-linear-gradient(left, #ffffff 10%, rgba(255, 255, 255, 0) 42%);
          background: -o-linear-gradient(left, #ffffff 10%, rgba(255, 255, 255, 0) 42%);
          background: -ms-linear-gradient(left, #ffffff 10%, rgba(255, 255, 255, 0) 42%);
          background: linear-gradient(to right, #ffffff 10%, rgba(255, 255, 255, 0) 42%);
          position: relative;
          -webkit-animation: load3 1.4s infinite linear;
          animation: load3 1.4s infinite linear;
          -webkit-transform: translateZ(0);
          -ms-transform: translateZ(0);
          transform: translateZ(0);
        }
        .loader:before {
          width: 50%;
          height: 50%;
          background: #ffffff;
          border-radius: 100% 0 0 0;
          position: absolute;
          top: 0;
          left: 0;
          content: '';
        }
        .loader:after {
          background: #333;
          width: 75%;
          height: 75%;
          border-radius: 50%;
          content: '';
          margin: auto;
          position: absolute;
          top: 0;
          left: 0;
          bottom: 0;
          right: 0;
        }
        @-webkit-keyframes load3 {
          0% {
            -webkit-transform: rotate(0deg);
            transform: rotate(0deg);
          }
          100% {
            -webkit-transform: rotate(360deg);
            transform: rotate(360deg);
          }
        }
        @keyframes load3 {
          0% {
            -webkit-transform: rotate(0deg);
            transform: rotate(0deg);
          }
          100% {
            -webkit-transform: rotate(360deg);
            transform: rotate(360deg);
          }
        }

        .loaded-container {
            display: none;
        }


    </style>
    <body>
      <div class="main-container">
          <div id="loader" class="loading-container">
              <div class="loader">Loading...</div>
          </div>

          <div id="main" class="loaded-container">
              <h1>Content is loaded!</h1>
          </div>
      </div>

      <script>
          setTimeout(function() {
              document.getElementById('loader').style.display = 'none'
              document.getElementById('main').style.display = 'block'
          }, 5000)
      </script>
    </body>
"""


if __name__ == '__main__':
    window = webview.create_window('Loading Animation', html=html, background_color='#333333')
    webview.start()
```