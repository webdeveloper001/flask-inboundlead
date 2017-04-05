const webpack = require('webpack');
const ExtractTextPlugin = require("extract-text-webpack-plugin");

module.exports = [
{
    entry: {
        clientEmbedCode: './static/client/src/template.js'
    },
    output: {
        path: './static/client/dist',
        filename: '[name].bundle.js'
    }
},
{
    entry: {
        modalEmbed: './static/modal-test/src/js/main.js'
    },
    output: {
        path: './static/modal-test/dist',
        filename: '[name].bundle.js'
    },
    module: {
        rules: [
            { test: /\.(html)$/, loader: 'html-loader'},
            {
                test: /\.less$/,
                use: ExtractTextPlugin.extract({
                  fallback: 'style-loader',
                  use: [
                    { loader: 'css-loader', options: { importLoaders: 1}},
                    { loader: 'postcss-loader', options: {
                        plugins: function () {
                          return [
                            require('autoprefixer')
                          ];
                        }
                      }
                    },
                    { loader: 'less-loader' }
                  ]
                })
            },
            { test: /\.(woff|woff2|eot|ttf|svg)$/, loader: 'file-loader?name=fonts/[hash].[ext]' },
        ]
    },
    plugins: [
        new webpack.ProvidePlugin({   
            jQuery: 'jquery',
            $: 'jquery',
            jquery: 'jquery'
        }),
        new ExtractTextPlugin("[name].css")
    ],
    resolve: {
        alias: { 
          'picker': 'pickadate/lib/picker'
        }
    }
}
];